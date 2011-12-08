var TopicTreeEditor = {
    tree: null,
    boundList: [],

    init: function() {
        var topicTree = getDefaultTopicTree();
        topicTree.bind("add", this.treeUpdate, topicTree);
        topicTree.bind("remove", this.treeUpdate, topicTree);
        topicTree.bind("clear", this.treeUpdate, topicTree);

        var root = topicTree.getRoot();
        root.bind("change", this.refreshTreeNode, root);
        root.fetch();

        // Attach the dynatree widget to an existing <div id="tree"> element
        // and pass the tree options as an argument to the dynatree() function:
        $("#topic_tree").dynatree({
            imagePath: '/images/',

            onActivate: function(node) {
                KAConsole.log('Activated: ', node);

                var model = null;
                if (node.data.kind == 'Topic') {
                    model = topicTree.get(node.data.key);
                } else if (node.data.kind == 'Video') {
                    model = new Video({ readable_id: node.data.key, title: 'Loading...' });
                } else if (node.data.kind == 'Exercise') {
                    model = new Exercise({ name: node.data.key, display_name: 'Loading...' });
                }

                TopicNodeEditor.init(node.data.kind, model);

                if (!model.inited)
                    model.fetch();
            },

            onCreate: function(node, span) {
                if (node.data.kind == 'Topic') {
                    $(span).contextMenu({menu: "topic_context_menu"}, function(action, el, pos) {
                        node.expand();
                        node.activate();
                        TopicTopicNodeEditor.handleAction(action, topicTree.get(node.data.key), topicTree.get(node.parent.data.key));
                    });
                }
            },

            onExpand: function(flag, node) {
                if (flag) {
                    node.activate();
                }
            },

            onLazyRead: function(node) {
                var model = topicTree.get(node.data.key);
                if (model.inited)
                    this.refreshTreeNode.call(model);
                else
                    model.fetch();
            },

            dnd: {
                onDragStart: function(node) {
                    return true;
                },

                onDragEnter: function(node, sourceNode) {
                    if (node.kind != 'Topic')
                        return ["before", "after"];

                    return ["over", "before", "after"];
                },
                onDragLeave: function(node, sourceNode) {
                },
                onDragOver: function(node, sourceNode, hitMode) {
                },

                onDrop: function(node, sourceNode, hitMode, ui, draggable) {
                    var oldParent = sourceNode.parent;

                    sourceNode.move(node, hitMode);

                    var data = {
                        kind: sourceNode.data.kind,
                        id: sourceNode.data.key,
                        new_parent_id: sourceNode.parent.data.key,
                        new_parent_pos: sourceNode.parent.childList.indexOf(sourceNode)
                    }
                    $.ajax({
                        url: '/api/v1/topic/' + oldParent.data.key + '/movechild',
                        type: 'POST',
                        data: data
                    });
                }
            },

            children: [ {
                    title: "Loading...",
                    key:  'root',
                    kind: 'Topic',
                    isFolder: true,
                    isLazy: true
            } ]
        });
        TopicTreeEditor.tree = $("#topic_tree").dynatree("getTree");
        $('#topic_tree').bind("mousedown", function(e) { e.preventDefault(); })
    },

    // Called with model as "this"
    refreshTreeNode: function() {
        var model = this;

        node = TopicTreeEditor.tree.getNodeByKey(model.id);
        if (!node)
            return;

        KAConsole.log('refreshing ' + model.id);

        node.setTitle(model.get("title"));

        node.removeChildren();
        if (model.get('children')) {
            _.each(model.get('children'), function(child) {
                var data = {
                    title: child.title,
                    key:  child.id,
                    kind: child.kind
                };
                if (child.kind == 'Topic') {
                    data.isFolder = true;
                    data.isLazy = true;
                    data.icon = 'leaf.png';
                } else if (child.kind == 'Video') {
                    data.icon = 'video-camera-icon-full-small.png';
                } else if (child.kind == 'Exercise') {
                    data.icon = 'exercise-icon-small.png';
                }
                node.addChild(data);
            });
        }
    },

    // Called with TopicTree as "this"
    treeUpdate: function() {
        this.each(function(childModel) {
            var found = false;
            _.each(TopicTreeEditor.boundList, function(childId) {
                if (childId == childModel.id)
                    found = true;
            });
            if (!found) {
                //KAConsole.log('Binding: ' + childModel.id);
                childModel.bind("change", TopicTreeEditor.refreshTreeNode, childModel);
                TopicTreeEditor.boundList.push(childModel.id);
            }
        });
    }
};

var TopicNodeEditor = {

    model: null,
    modelKind: null,
    template: null,

    init: function(kind, model) {
        TopicNodeEditor.modelKind = kind;
        TopicNodeEditor.model = model;
        TopicNodeEditor.template = Templates.get("topicsadmin.edit-" + kind.toLowerCase());

        TopicNodeEditor.render();

        model.bind("change", TopicNodeEditor.render);
    }, 

    render: function() {
        js = TopicNodeEditor.model.toJSON();
        html = TopicNodeEditor.template({model: js});

        $('#details_view').html(html);

        if (TopicNodeEditor.modelKind == 'Topic') {
            TopicTopicNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Exercise') {
            TopicExerciseNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Video') {
            TopicVideoNodeEditor.init();
        }
    }
};

var TopicAddExistingItemView = Backbone.View.extend({
    template: Templates.get( "topicsadmin.add-existing-item" ),
    loaded: false,
    type: '',

    initialize: function() {
        this.render();
    },

    events: {
        'click .do_search': 'doSearch',
        'click .show_recent': 'showRecent',
        'click .ok_button': 'selectItem'
    },

    render: function() {
        this.el = $(this.template({type: this.type})).appendTo(document.body).get(0);
        this.delegateEvents();
        return this;
    },

    show: function(type) {
        $(this.el).modal({
            keyboard: true,
            backdrop: true,
            show: true
        });

        if (type != this.type)
            this.loaded = false;
        this.type = type;

        $(this.el).find('.title').html('Choose ' + type + ':');

        if (!this.loaded) {
            this.showRecent();
        }
    },

    showResults: function(json) {
        var html = '';
        var self = this;
        _.each(json, function(item) {
            if (self.type == 'video') {
                html += '<option value="' + item.readable_id + '">' + item.title + '</option>';
            } else {
                html += '<option value="' + item.name + '">' + item.display_name + '</option>';
            }
        });
        $(this.el).find('select.search_results').html(html);
    },

    showRecent: function() {
        var self = this;

        if (this.type == 'video')
            $(this.el).find('.search_description').html('Most recent videos:');
        else
            $(this.el).find('.search_description').html('Most recent exercises:');
        self.showResults([{
            readable_id: '',
            name: '',
            title: 'Loading...',
            display_name: 'Loading...'
        }]);

        var url;
        if (this.type == 'video')
            url = '/api/v1/videos_recent';
        else
            url = '/api/v1/exercises_recent';
        $.ajax({
            url: url,

            success: function(json) {
                self.loaded = true;
                self.showResults(json);
            }
        });
    },

    doSearch: function() {
        var searchText = $(this.el).find('input[name="item_search"]').val();
        var self = this;

        if (this.type == 'video')
            $(this.el).find('.search_description').html('Videos matching "' + searchText + '":');
        else
            $(this.el).find('.search_description').html('Exercises matching "' + searchText + '":');
        self.showResults([{
            readable_id: '',
            name: '',
            title: 'Loading...',
            display_name: 'Loading...'
        }]);

        $.ajax({
            url: '/api/v1/autocomplete?q=' + encodeURIComponent(searchText),

            success: function(json) {
                self.loaded = true;
                if (self.type == 'video')
                    self.showResults(json.videos);
                else
                    self.showResults(json.exercises);
            }
        });
    },

    selectItem: function() {
        var itemID = $(this.el).find('select.search_results option:selected').val();
        if (!itemID)
            return;

        TopicTopicNodeEditor.finishAddExistingItem(this.type, itemID);
    },

    hide: function() {
        return $(this.el).modal('hide');
    }
});

var TopicTopicNodeEditor = {
    existingItemView: null,
    contextModel: null,

    addTag: function() {
        var tag = $("#add-tag").val();

        if (tag) {
            var tags = TopicNodeEditor.model.get('tags').slice(0);

            tags.push(tag);
            TopicNodeEditor.model.set({tags: tags}); // This triggers a TopicNodeEditor.render()
            TopicNodeEditor.model.save();
        }
    },
    deleteTag: function(tag) {
        var tags = TopicNodeEditor.model.get('tags').slice(0);

        var idx = tags.indexOf(tag);
        if (idx >= 0) {
            tags.splice(idx, 1);
            TopicNodeEditor.model.set({tags: tags}); // This triggers a TopicNodeEditor.render()
            TopicNodeEditor.model.save();
        }
    },

    handleAction: function(action, model, parent_model) {
        if (!model)
            model = TopicNodeEditor.model;

        if (action == 'add_existing_video') {
            if (!TopicTopicNodeEditor.existingItemView)
                TopicTopicNodeEditor.existingItemView = new TopicAddExistingItemView();

            TopicTopicNodeEditor.contextModel = model;
            TopicTopicNodeEditor.existingItemView.show('video');

        } else if (action == 'add_existing_exercise') {
            if (!TopicTopicNodeEditor.existingItemView)
                TopicTopicNodeEditor.existingItemView = new TopicAddExistingItemView();

            TopicTopicNodeEditor.contextModel = model;
            TopicTopicNodeEditor.existingItemView.show('exercise');

        } else if (action == 'delete_topic') {
            data = {
                kind: 'Topic',
                id: model.id
            };
            $.ajax({
                url: '/api/v1/topic/' + parent_model.id + '/deletechild',
                type: 'POST',
                data: data,
                success: function(json) {
                    child_list = parent_model.get('children').slice(0);
                    child_list.splice(child_list.indexOf(model.id), 1);    
                    parent_model.set('children', child_list);
                }
            });
        }
    },

    finishAddExistingItem: function(type, id) {
        TopicTopicNodeEditor.existingItemView.hide();

        var kind;
        if (type == 'video')
            kind = 'Video';
        else
            kind = 'Exercise';

        KAConsole.log('Adding ' + kind + ' ' + id + ' to Topic ' + TopicTopicNodeEditor.contextModel.get('title'));
        var data = {
            kind: kind,
            id: id,
            pos: TopicTopicNodeEditor.contextModel.get('children').length
        };
        $.ajax({
            url: '/api/v1/topic/' + TopicTopicNodeEditor.contextModel.get('id') + '/addchild',
            type: 'POST',
            data: data,
            success: function(json) {
                KAConsole.log('Added item successfully.');
                TopicTopicNodeEditor.contextModel.set(json);
            }
        });
    },

    init: function() {
        $('#details_view').find('input').change(function() {
            var field = $(this).attr('name');
            if (field) {
                var value = $(this).val();
                var setter = {};
                setter[field] = value;
                TopicNodeEditor.model.set(setter);
                TopicNodeEditor.model.save();
            }
        });
    }
};

var TopicExerciseNodeEditor = {
    addCover: function() {
        var cover = $("#add-cover").val();

        if (cover) {
            var covers = TopicNodeEditor.model.get('covers').slice(0);

            covers.push(cover);
            TopicNodeEditor.model.set({covers: covers}); // This triggers a TopicNodeEditor.render()
        }
    },
    deleteCover: function(cover) {
        var covers = TopicNodeEditor.model.get('covers').slice(0);

        var idx = covers.indexOf(cover);
        if (idx >= 0) {
            covers.splice(idx, 1);
            TopicNodeEditor.model.set({covers: covers}); // This triggers a TopicNodeEditor.render()
        }
    },

    addPrereq: function() {
        var prereq = $("#add-prereq").val();

        if (prereq) {
            var prereqs = TopicNodeEditor.model.get('prerequisites').slice(0);

            prereqs.push(prereq);
            TopicNodeEditor.model.set({prerequisites: prereqs}); // This triggers a TopicNodeEditor.render()
        }
    },
    deletePrereq: function(prereq) {
        var prereqs = TopicNodeEditor.model.get('prerequisites').slice(0);

        var idx = prereqs.indexOf(prereq);
        if (idx >= 0) {
            prereqs.splice(idx, 1);
            TopicNodeEditor.model.set({prerequisites: prereqs}); // This triggers a TopicNodeEditor.render()
        }
    },

    init: function() {
        // TomY TODO - related videos

        $('#details_view').find('input').change(function() {
            var field = $(this).attr('name');
            if (field) {
                var value = $(this).val();
                var setter = {};
                setter[field] = value;
                TopicNodeEditor.model.set(setter);
            }
        });

        // Configure the search form
        $('#related-videos-input').placeholder();
        initAutocomplete("#related-videos-input", false, TopicExerciseNodeEditor.addVideo, true);
    }
};

var TopicVideoNodeEditor = {
    init: function() {
        // TomY TODO - related videos

        $('#details_view').find('input').change(function() {
            var field = $(this).attr('name');
            if (field) {
                var value = $(this).val();
                var setter = {};
                setter[field] = value;
                TopicNodeEditor.model.set(setter);
            }
        });
    }
};
