// Creates & handles events for the topic tree

var TopicTreeEditor = {
    tree: null,
    boundList: [],

    init: function() {
        // Attach the dynatree widget to an existing <div id="tree"> element
        // and pass the tree options as an argument to the dynatree() function:
        $("#topic_tree").dynatree({
            imagePath: '/images/',

            onActivate: function(node) {
                KAConsole.log('Activated: ', node);

                TopicNodeEditor.init();

                if (node.data.kind == 'Topic' && node.data.key != 'root') {
                    topicTree.fetchByID(node.data.key, TopicNodeEditor.initModel, [node]);
                } else if (node.data.kind == 'Video') {
                    getVideoList().fetchByID(node.data.key, TopicNodeEditor.initModel, [node]);
                } else if (node.data.kind == 'Exercise') {
                    getExerciseList().fetchByID(node.data.key, TopicNodeEditor.initModel, [node]);
                } else {
                    $('#details-view').html('');
                }
            },

            onCreate: function(node, span) {
                if (node.data.kind == 'Topic') {
                    $(span).contextMenu({menu: "topic_context_menu"}, function(action, el, pos) {
                        topicTree.fetchByID(node.data.key, function() {
                            TopicTopicNodeEditor.handleAction(action, node, this, topicTree.get(node.parent.data.key));
                        });
                    });
                }
                if (node.data.kind == 'Video' || node.data.kind == 'Exercise') {
                    $(span).contextMenu({menu: "item_context_menu"}, function(action, el, pos) {
                        TopicItemNodeEditor.handleAction(action, node, node.data.kind, node.data.key, topicTree.get(node.parent.data.key));
                    });
                }
            },

            onExpand: function(flag, node) {
                if (flag) {
                    node.activate();
                }
            },

            onLazyRead: function(node) {
                topicTree.fetchByID(node.data.key);
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

                    var newParent = sourceNode.parent;

                    var data = {
                        kind: sourceNode.data.kind,
                        id: sourceNode.data.key,
                        new_parent_id: newParent.data.key,
                        new_parent_pos: newParent.childList.indexOf(sourceNode)
                    }
                    TopicTopicNodeEditor.moveItem(oldParent.data.key, data); 
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

        var self = this;
        $(window).resize(function(){self.resize();});
        this.resize();

        // Get the data for the topic tree (may fire callbacks immediately)

        var topicTree = getDefaultTopicTree();
        topicTree.bind("add", this.treeUpdate, topicTree);
        topicTree.bind("remove", this.treeUpdate, topicTree);
        topicTree.bind("clear", this.treeUpdate, topicTree);

        var root = topicTree.getRoot();
        root.bind("change", this.refreshTreeNode, root);
    },

    resize: function() {
        var containerHeight = $(window).height();
        var yTopPadding = $('#topic_tree').offset().top;
        var newHeight = containerHeight - (yTopPadding + 42);

        $('#topic_tree').height(newHeight);
        $('#details-view').height(newHeight);
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
                    if (child.hide) {
                        data.addClass = 'hidden-topic';
                        data.title = child.title + ' [Hidden]';
                    }
                } else if (child.kind == 'Video') {
                    data.icon = 'video-camera-icon-full-small.png';
                } else if (child.kind == 'Exercise') {
                    data.icon = 'exercise-icon-small.png';
                }
                node.addChild(data);
            });
        }

        if (model.id == 'root') {
            node.expand();
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

// Details view common code

var TopicNodeEditor = {

    node: null,
    model: null,
    parentModel: null,
    modelKind: null,
    template: null,

    init: function(kind, model, parentModel) {
        if (TopicNodeEditor.model) {
            TopicNodeEditor.model.unbind("change", TopicNodeEditor.render);
        }

        $('#details-view').html('<div style="left: 350px; position: relative; width: 10px;"><div class="dialog-progress-bar"></div></div>');
        $("#details-view .dialog-progress-bar").progressbar();
        $("#details-view .dialog-progress-bar").progressbar('value', 100);
    }, 

    initModel: function(node) {
        TopicNodeEditor.node = node;
        TopicNodeEditor.modelKind = node.data.kind;
        TopicNodeEditor.model = this;
        TopicNodeEditor.parentModel = getDefaultTopicTree().get(node.parent.data.key);
        TopicNodeEditor.template = Templates.get("topicsadmin.edit-" + node.data.kind.toLowerCase());

        TopicNodeEditor.render();

        this.bind("change", TopicNodeEditor.render);
    },

    render: function() {
        js = TopicNodeEditor.model.toJSON();
        html = TopicNodeEditor.template({model: js});

        $('#details-view').html(html);

        if (TopicNodeEditor.modelKind == 'Topic') {
            TopicTopicNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Exercise') {
            TopicExerciseNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Video') {
            TopicVideoNodeEditor.init();
        }
    }
};

// Details view & editing functions for topics

var TopicTopicNodeEditor = {
    existingItemView: null,
    newExerciseView: null,
    newVideoView: null,
    contextNode: null,
    contextModel: null,
    itemCopyBuffer: null,

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

    handleAction: function(action, node, model, parentModel) {
        if (!node)
            node = TopicNodeEditor.node;    
        if (!model)
            model = TopicNodeEditor.model;
        if (!parentModel)
            parentModel = TopicNodeEditor.parentModel;

        TopicTopicNodeEditor.contextNode = node;
        TopicTopicNodeEditor.contextModel = model;

        if (action == 'add_new_topic') {
            var topic = new Topic();
            KAConsole.log('Creating new topic...');
            topic.save({}, {
                success: function() {
                    KAConsole.log('Created new topic:', topic.id);
                    var data = {
                        kind: 'Topic',
                        id: topic.id,
                        pos: model.get('children').length
                    };
                    $.ajax({
                        url: '/api/v1/topic/' + model.id + '/addchild',
                        type: 'POST',
                        data: data,
                        success: function(json) {
                            KAConsole.log('Added topic successfully.');
                            model.set(json);

                            node.expand();
                            node.getChildren()[data.pos].activate();
                        }
                    });
                }
            });

        } else if (action == 'add_new_video') {
            if (!TopicTopicNodeEditor.newVideoView)
                TopicTopicNodeEditor.newVideoView = new TopicCreateVideoView();

            TopicTopicNodeEditor.newVideoView.show();

        } else if (action == 'add_existing_video') {
            if (!TopicTopicNodeEditor.existingItemView)
                TopicTopicNodeEditor.existingItemView = new TopicAddExistingItemView();

            TopicTopicNodeEditor.existingItemView.show('video');

        } else if (action == 'add_new_exercise') {
            if (!TopicTopicNodeEditor.newExerciseView)
                TopicTopicNodeEditor.newExerciseView = new TopicCreateExerciseView();

            TopicTopicNodeEditor.newExerciseView.show();

        } else if (action == 'add_existing_exercise') {
            if (!TopicTopicNodeEditor.existingItemView)
                TopicTopicNodeEditor.existingItemView = new TopicAddExistingItemView();

            TopicTopicNodeEditor.existingItemView.show('exercise');

        } else if (action == 'paste_item') {

            if (!TopicTopicNodeEditor.itemCopyBuffer)
                return;

            if (TopicTopicNodeEditor.itemCopyBuffer.type == 'copy') {
                TopicTopicNodeEditor.finishAddExistingItem(TopicTopicNodeEditor.itemCopyBuffer.kind, TopicTopicNodeEditor.itemCopyBuffer.id);

            } else if (TopicTopicNodeEditor.itemCopyBuffer.type == 'cut') {
                var data = {
                    kind: TopicTopicNodeEditor.itemCopyBuffer.kind,
                    id: TopicTopicNodeEditor.itemCopyBuffer.id,
                    new_parent_id: model.id,
                    new_parent_pos: model.get('children').length
                }
                TopicTopicNodeEditor.moveItem(TopicTopicNodeEditor.itemCopyBuffer.originalParent, data);
            }

        } else if (action == 'delete_topic') {
            data = {
                kind: 'Topic',
                id: model.id
            };
            $.ajax({
                url: '/api/v1/topic/' + parentModel.id + '/deletechild',
                type: 'POST',
                data: data,
                success: function(json) {
                    parentModel.removeChild('Topic', model.id);
                }
            });
        }
    },

    finishAddExistingItem: function(kind, id) {

        KAConsole.log('Adding ' + kind + ' ' + id + ' to Topic ' + TopicTopicNodeEditor.contextModel.get('title'));
        var data = {
            kind: kind,
            id: id,
            pos: TopicTopicNodeEditor.contextModel.get('children').length
        };
        $.ajax({
            url: '/api/v1/topic/' + TopicTopicNodeEditor.contextModel.id + '/addchild',
            type: 'POST',
            data: data,
            success: function(json) {
                KAConsole.log('Added item successfully.');
                TopicTopicNodeEditor.contextModel.set(json);

                TopicTopicNodeEditor.contextNode.expand();
                TopicTopicNodeEditor.contextNode.getChildren()[data.pos].activate();
            }
        });
    },


    moveItem: function(oldParentID, moveData) {
        $.ajax({
            url: '/api/v1/topic/' + oldParentID + '/movechild',
            type: 'POST',
            data: moveData,
            success: function() {
                child = getDefaultTopicTree().get(oldParentID).removeChild(moveData.kind, moveData.id);
                getDefaultTopicTree().get(moveData.new_parent_id).addChild(child, moveData.new_parent_pos);

                parent_node = TopicTreeEditor.tree.getNodeByKey(moveData.new_parent_id);
                parent_node.expand();
                parent_node.getChildren()[moveData.new_parent_pos].activate();
            },
            error: function() {
                // ?
            }
        });
    },

    init: function() {
        $('#details-view').find('input').change(function() {
            var field = $(this).attr('name');
            if (field) {
                var value = null;
                if (this.type == 'checkbox')
                    value = $(this).is(':checked');
                else
                    value = $(this).val();

                var setter = {};
                setter[field] = value;
                TopicNodeEditor.model.set(setter);

                TopicNodeEditor.model.save();
            }
        });
    }
};

// Details view common code for videos/exercises

var TopicItemNodeEditor = {
    init: function() {
        $('#details-view').find('input').change(function() {
            unsavedChanges = false;
            inputElements = $('#details-view input[type="text"]');
            inputElements.add('#details-view input[type="radio"]:checked');
            inputElements.each(function() {
                var field = $(this).attr('name');
                if (field) {
                    if ((''+TopicNodeEditor.model.get(field)) != $(this).val())
                        unsavedChanges = true;
                }
            });
            if (unsavedChanges) {
                $('#details-view .save-button').removeClass('disabled').addClass('green');
            } else {
                $('#details-view .save-button').addClass('disabled').removeClass('green');
            }
        });
    },

    handleAction: function(action, node, kind, id, parentModel) {
        if (!kind)
            kind = TopicNodeEditor.modelKind;
        if (!id)
            id = TopicNodeEditor.model.id;
        if (!parentModel)
            parentModel = TopicNodeEditor.parentModel;

        if (action == 'save') {
            attrs = {};
            inputElements = $('#details-view input[type="text"]');
            inputElements.add('#details-view input[type="radio"]:checked');
            inputElements.each(function() {
                var field = $(this).attr('name');
                if (field) {
                    if ((''+TopicNodeEditor.model.get(field)) != $(this).val()) {
                        attrs[field] = $(this).val();
                    }
                }
            });

            if (attrs != {}) {
                Throbber.show($("#details-view .save-button"), true);
                TopicNodeEditor.model.save(attrs, {
                    success: function() {
                        Throbber.hide();
                    }
                });
            }

        } else if (action == 'copy_item') {
            TopicTopicNodeEditor.itemCopyBuffer = {
                type: 'copy',
                kind: kind,
                id: id
            };

        } else if (action == 'cut_item') {
            TopicTopicNodeEditor.itemCopyBuffer = {
                type: 'cut',
                kind: kind,
                id: id,
                originalParent: parentModel.id
            };

        } else if (action == 'remove_item') {
            data = {
                kind: kind,
                id: id
            };
            $.ajax({
                url: '/api/v1/topic/' + parentModel.id + '/deletechild',
                type: 'POST',
                data: data,
                success: function(json) {
                    parentModel.removeChild(kind, id);
                }
            });

        }
    }
};

// Details view for exercises

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

        TopicItemNodeEditor.init();

        // Configure the search form
        $('#related-videos-input').placeholder();
        initAutocomplete("#related-videos-input", false, TopicExerciseNodeEditor.addVideo, true);
    }
};

// Details view for videos

var TopicVideoNodeEditor = {
    init: function() {
        TopicItemNodeEditor.init();
    }
};

// Add existing video/exercise dialog box

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

        this.hide();

        var kind;
        if (this.type == 'video')
            kind = 'Video';
        else
            kind = 'Exercise';

        TopicTopicNodeEditor.finishAddExistingItem(kind, itemID);
    },

    hide: function() {
        return $(this.el).modal('hide');
    }
});

// Add a new exercise dialog box

var TopicCreateExerciseView = Backbone.View.extend({
    template: Templates.get( "topicsadmin.create-exercise" ),

    initialize: function() {
        this.render();
    },

    events: {
        'click .ok_button': 'createExercise'
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
    },

    createExercise: function() {
        var name = $(this.el).find('input[name="name"]').val();
        var exercise = new Exercise({ name: name });
        if ($(this.el).find('input[name="summative"]').is(':checked'))
            exercise.set({ summative: true });

        exercise.save({}, {
            success: function() {
                TopicTopicNodeEditor.finishAddExistingItem('Exercise', name);
            }
        });
        this.hide();
    },

    hide: function() {
        return $(this.el).modal('hide');
    }
});

// Add a new video dialog box

var TopicCreateVideoView = Backbone.View.extend({
    template: Templates.get( "topicsadmin.create-video" ),
    previewTemplate: Templates.get( "topicsadmin.create-video-preview" ),

    youtubeID: null,

    initialize: function() {
        this.render();
    },

    events: {
        'click .ok_button': 'createVideo',
        'change input[name="youtube_id"]': 'doVideoSearch'
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

        this.youtubeID = null;
        $(this.el).find('.create-video-preview').html("Enter a YouTube ID to look up a video.");
        $(self.el).find('.ok_button').addClass('disabled').removeClass('green');
    },

    createVideo: function() {
        if (!this.youtubeID)
            return;

        var video = new Video({ youtube_id: this.youtubeID });

        video.save({}, {
            success: function(model) {
                TopicTopicNodeEditor.finishAddExistingItem('Video', model.get('readable_id'));
            }
        });
        this.hide();
    },

    doVideoSearch: function() {
        var youtubeID = $(this.el).find('input[name="youtube_id"]').val();
        var self = this;
        $.ajax({
            url: '/api/v1/videos/youtubeinfo/' + youtubeID,
            success: function(json) {
                self.youtubeID = youtubeID;
                $(self.el).find('.create-video-preview').html(self.previewTemplate(json));
                $(self.el).find('.ok_button').removeClass('disabled').addClass('green');
            },
            error: function(json) {
                self.youtubeID = null;
                $(self.el).find('.create-video-preview').html("Video not found.");
                $(self.el).find('.ok_button').addClass('disabled').removeClass('green');
            },
        });
    },

    hide: function() {
        return $(this.el).modal('hide');
    }
});
