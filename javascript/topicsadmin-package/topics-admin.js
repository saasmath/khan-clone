// Creates & handles events for the topic tree

var debugNodeIDs = true;

var TopicTreeEditor = {
    tree: null,
    boundList: [],
    maxProgressLength: 0,
    currentVersion: null,

    init: function(version) {
        var topicTree = version.getTopicTree();
        this.currentVersion = version;

        // Attach the dynatree widget to an existing <div id="tree"> element
        // and pass the tree options as an argument to the dynatree() function:
        $("#topic_tree").dynatree({
            imagePath: '/images/',

            onActivate: function(node) {
                KAConsole.log('Activated: ', node);

                TopicNodeEditor.init();

                if (node.data.kind == 'Topic' && node.data.id != 'root') {
                    topicTree.fetchByID(node.data.id, TopicNodeEditor.initModel, [node]);
                } else if (node.data.kind == 'Video') {
                    getVideoList().fetchByID(node.data.id, TopicNodeEditor.initModel, [node]);
                } else if (node.data.kind == 'Exercise') {
                    getExerciseList().fetchByID(node.data.id, TopicNodeEditor.initModel, [node]);
                } else if (node.data.kind == 'Url') {
                    getUrlList().fetchByID(node.data.id, TopicNodeEditor.initModel, [node]);
                } else {
                    $('#details-view').html('');
                }
            },

            onCreate: function(node, span) {
                if (node.data.kind == 'Topic') {
                    $(span).contextMenu({menu: "topic_context_menu"}, function(action, el, pos) {
                        topicTree.fetchByID(node.data.id, function() {
                            TopicTopicNodeEditor.handleAction(action, node, this, topicTree.get(node.parent.data.id));
                        });
                    });
                }
                if (node.data.kind == 'Video' || node.data.kind == 'Exercise' || node.data.kind == 'Url') {
                    $(span).contextMenu({menu: "item_context_menu"}, function(action, el, pos) {
                        TopicItemNodeEditor.handleAction(action, node, node.data.kind, node.data.id, topicTree.get(node.parent.data.id));
                    });
                }
            },

            onExpand: function(flag, node) {
                if (flag) {
                    node.activate();
                }
            },

            onLazyRead: function(node) {
                topicTree.fetchByID(node.data.id, TopicTreeEditor.refreshTreeNode);
            },

            dnd: {
                onDragStart: function(node) {
                    return TopicTreeEditor.currentVersion.get('edit');
                },

                onDragEnter: function(node, sourceNode) {
                    if (node.data.kind != 'Topic')
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
                        id: sourceNode.data.id,
                        new_parent_id: newParent.data.id,
                        new_parent_pos: newParent.childList.indexOf(sourceNode)
                    }
                    TopicTopicNodeEditor.moveItem(oldParent.data.id, data); 
                }
            },

            children: [ {
                    title: "Loading...",
                    key: 'Topic/root',
                    id: 'root',
                    kind: 'Topic',
                    isFolder: true,
                    isLazy: true,
                    icon: 'topictree-icon-small.png'
            } ]
        });
        TopicTreeEditor.tree = $("#topic_tree").dynatree("getTree");
        $('#topic_tree').bind("mousedown", function(e) { e.preventDefault(); })

        $('#details-view').html('');

        $('#topicversion-editor').html(Templates.get("topicsadmin.edit-version")(version.toJSON()));

        $('#topictree-queue-progress-bar').progressbar();
        $('#topictree-queue-progress-bar').progressbar("value", 0);
        $('#topictree-queue-progress-bar').progressbar("disable");
        $('#topictree-queue-progress-text').html('');

        var self = this;
        $(window).resize(function(){self.resize();});
        this.resize();

        // Get the data for the topic tree (may fire callbacks immediately)

        topicTree.bind("add", this.treeUpdate, topicTree);
        topicTree.bind("remove", this.treeUpdate, topicTree);
        topicTree.bind("clear", this.treeUpdate, topicTree);

        var root = topicTree.getRoot();
        root.bind("change", this.refreshTreeNode, root);
        if (root.__inited)
            this.refreshTreeNode.apply(root);

        this.updateProgressBar();
    },

    updateProgressBar: function() {
        if (document.ajaxq && document.ajaxq.q['topics-admin'] &&
            document.ajaxq.q['topics-admin'].length > 0) {
            $('#topictree-queue-progress-bar').progressbar("enable");

            var remaining = document.ajaxq.q['topics-admin'].length;
            if (TopicTreeEditor.maxProgressLength < remaining)
                TopicTreeEditor.maxProgressLength = remaining;

            $('#topictree-queue-progress-bar').progressbar("value", (1 - (remaining / TopicTreeEditor.maxProgressLength)) * 100);
            $('#topictree-queue-progress-text').html('Updating (' + (TopicTreeEditor.maxProgressLength - remaining + 1) + ' / ' + TopicTreeEditor.maxProgressLength + ')');

        } else {
            if (TopicTreeEditor.maxProgressLength > 0) {
                $('#topictree-queue-progress-text').html('Done updating.');
                $('#topictree-queue-progress-bar').progressbar("value", 100);
                TopicTreeEditor.maxProgressLength = 0; // 1 second delay before we wipe the progress
            } else {
                $('#topictree-queue-progress-bar').progressbar("value", 0);
                $('#topictree-queue-progress-bar').progressbar("disable");
            }
        }

        setTimeout(TopicTreeEditor.updateProgressBar, 1000);
    },

    resize: function() {
        var containerHeight = $(window).height();
        var yTopPadding = $('#topic_tree').offset().top;
        var newHeight = containerHeight - (yTopPadding + 42);

        $('#topic_tree').height(newHeight);
        $('#details-view').height(newHeight);
    },

    createChild: function(kind, id, title, hide) {
        var data = {
            title: title,
            key:  kind + '/' + id,
            id: id,
            kind: kind
        };
        if (debugNodeIDs) {
            data.title += ' [(' + id + ')]';
        }
        if (kind == 'Topic') {
            data.isFolder = true;
            data.isLazy = true;
            data.icon = 'leaf-icon-small.png';
            if (hide) {
                data.addClass = 'hidden-topic';
                data.title = title + ' [Hidden]';
            }
        } else if (kind == 'Video') {
            data.icon = 'video-camera-icon-full-small.png';
        } else if (kind == 'Exercise') {
            data.icon = 'exercise-icon-small.png';
        } else if (kind == 'Url') {
            data.icon = 'link-icon-small.png';
        }
        return data;
    },

    // Called with model as "this"
    refreshTreeNode: function() {
        var model = this;

        node = TopicTreeEditor.tree.getNodeByKey(model.get('kind') + '/' + model.id);
        if (!node)
            return;

        KAConsole.log('refreshing ' + model.id);

        if (debugNodeIDs) {
            node.setTitle(model.get("title") + ' [' + model.id + ']');
        } else {
            node.setTitle(model.get("title"));
        }

        node.removeChildren();
        if (model.get('children')) {
            childNodes = []
            _.each(model.get('children'), function(child) {
                childNodes.push(TopicTreeEditor.createChild(child.kind, child.id, child.title, child.hide));
            });
            node.addChild(childNodes);
        }

        if (model.id == 'root') {
            node.expand();
        }
    },

	handleChange: function(model, oldID) {
		var kind = model.get('kind');
		var title_field = 'title';
		if (kind == 'Exercise')
			title_field = 'display_name';

		KAConsole.log('Model of type ' + kind + ' changed ID: ' + oldID + ' -> ' + model.id);

		TopicTreeEditor.currentVersion.getTopicTree().each(function(topic) {
			var found = false;
			var children = _.map(topic.get('children'), function(child) {
				if (child.kind == kind && child.id == oldID) {
					var new_child = {
						id: model.id,
						kind: kind,
						title: model.get(title_field),
						hide: child.hide
					};

					found = true;

					return new_child;
				} else {
					return child;
				}
			});
			if (found)
				topic.set({children: children});
		});
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
    },

    setTreeDefault: function() {
        popupGenericMessageBox({
            title: "Confirm publish topic tree",
            message: "Marking this version of the topic tree default will publish all changes to the live version of the website. Are you sure?",
            buttons: [
                { title: "Yes", action: TopicTreeEditor.doSetTreeDefault },
                { title: "No", action: hideGenericMessageBox }
            ]
        });
    },

    doSetTreeDefault: function() {
        hideGenericMessageBox();
        popupGenericMessageBox({
            title: "Publishing topic tree",
            message: "Publishing topic tree. Please wait...",
            buttons: []
        });
        $.ajaxq('topics-admin', {
            url: '/api/v1/topicversion/edit/setdefault',
            success: function() {
                hideGenericMessageBox();
                popupGenericMessageBox({
                    title: "Topic tree published",
                    message: "Topic tree has been published to the live site.",
                    buttons: null
                });
            },
            error: function() {
                // TomY TODO handle error
            }
        });
    },

    showVersionList: function() {
        this.versionListView = new TopicVersionListView().show();
    },

    editVersion: function(versionNumber) {
        this.versionListView.hide();

        version = getTopicVersionList().get(versionNumber);
        if (version)
            this.init(version)
    },
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
        TopicNodeEditor.parentModel = TopicTreeEditor.currentVersion.getTopicTree().get(node.parent.data.id);
        TopicNodeEditor.template = Templates.get("topicsadmin.edit-" + node.data.kind.toLowerCase());

        TopicNodeEditor.render();

        this.bind("change", TopicNodeEditor.render);
    },

    render: function() {
        js = TopicNodeEditor.model.toJSON();
        html = TopicNodeEditor.template({version: TopicTreeEditor.currentVersion.toJSON(), model: js});

        $('#details-view').html(html);

        TopicExerciseNodeEditor.deinit();
        TopicUrlNodeEditor.deinit();

        if (TopicNodeEditor.modelKind == 'Topic') {
            TopicTopicNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Exercise') {
            TopicExerciseNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Video') {
            TopicVideoNodeEditor.init();
        } else if (TopicNodeEditor.modelKind == 'Url') {
            TopicUrlNodeEditor.init();
        } 
    }
};

// Details view & editing functions for topics

var TopicTopicNodeEditor = {
    existingItemView: null,
    newExerciseView: null,
    newVideoView: null,
    newUrlView: null,
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
                    $.ajaxq('topics-admin', {
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

            TopicTopicNodeEditor.existingItemView.show('video', TopicTopicNodeEditor.finishAddExistingItem);

        } else if (action == 'add_new_exercise') {
            if (!TopicTopicNodeEditor.newExerciseView)
                TopicTopicNodeEditor.newExerciseView = new TopicCreateExerciseView();

            TopicTopicNodeEditor.newExerciseView.show();

        } else if (action == 'add_existing_exercise') {
            if (!TopicTopicNodeEditor.existingItemView)
                TopicTopicNodeEditor.existingItemView = new TopicAddExistingItemView();

            TopicTopicNodeEditor.existingItemView.show('exercise', TopicTopicNodeEditor.finishAddExistingItem);

        } else if (action == 'add_new_url') {
            if (!TopicTopicNodeEditor.newUrlView)
                TopicTopicNodeEditor.newUrlView = new TopicCreateUrlView();

            TopicTopicNodeEditor.newUrlView.show();

        } else if (action == 'paste_item') {

            if (!TopicTopicNodeEditor.itemCopyBuffer)
                return;

            if (TopicTopicNodeEditor.itemCopyBuffer.type == 'copy') {
                TopicTopicNodeEditor.finishAddExistingItem(TopicTopicNodeEditor.itemCopyBuffer.kind, TopicTopicNodeEditor.itemCopyBuffer.id, TopicTopicNodeEditor.itemCopyBuffer.title, null, null, -1);

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
            $.ajaxq('topics-admin', {
                url: '/api/v1/topic/' + parentModel.id + '/deletechild',
                type: 'POST',
                data: data,
                success: function(json) {
                    parentModel.removeChild('Topic', model.id);
                }
            });
        }
    },

    finishAddExistingItem: function(kind, id, title, node, model, pos) {

        if (!model)
            model = TopicTopicNodeEditor.contextModel;
        if (!node)
            node = TopicTopicNodeEditor.contextNode;
        if (pos < 0)
            pos = model.get('children').length

        KAConsole.log('Adding ' + kind + ' ' + id + ' to Topic ' + model.get('title'));

        var newChild = {
            kind: kind,
            id: id,
            title: title
        };
        children = model.get('children').slice(0);
        children.splice(pos, 0, newChild);
        model.set({ children: children });

        node.expand();
        node.getChildren()[pos].activate();

        var data = {
            kind: kind,
            id: id,
            pos: pos
        };
        $.ajaxq('topics-admin', {
            url: '/api/v1/topic/' + model.id + '/addchild',
            type: 'POST',
            data: data,
            success: function(json) {
                KAConsole.log('Added item successfully.');
            }
        });
    },


    moveItem: function(oldParentID, moveData) {
        // Apply the change to the model data first
        child = TopicTreeEditor.currentVersion.getTopicTree().get(oldParentID).removeChild(moveData.kind, moveData.id);
        new_parent = TopicTreeEditor.currentVersion.getTopicTree().fetchByID(moveData.new_parent_id, function() {
            this.addChild(child, moveData.new_parent_pos);

            parent_node = TopicTreeEditor.tree.getNodeByKey('Topic/' + moveData.new_parent_id);
            parent_node.expand();
            parent_node.getChildren()[moveData.new_parent_pos].activate();

            $.ajaxq('topics-admin', {
                url: '/api/v1/topic/' + oldParentID + '/movechild',
                type: 'POST',
                data: moveData,
                success: function() {
                },
                error: function() {
                    // ?
                }
            });
        });
    },

    init: function() {
        if (TopicTreeEditor.currentVersion.get('edit')) {
            $('#details-view').find('input').change(function() {
                var field = $(this).attr('name');
                if (field) {
                    var value = null;
                    if (this.type == 'checkbox')
                        value = $(this).is(':checked');
                    else
                        value = $(this).val();

                    var attrs = {};
                    var oldID = TopicNodeEditor.model.id;
                    attrs[field] = value;

                    // We do special things on save because of the potential ID change
                    TopicNodeEditor.model.save(attrs, {
                        url: TopicNodeEditor.model.url(), // URL with the old slug value
                        success: function() { TopicTreeEditor.handleChange(TopicNodeEditor.model, oldID); }
                    });
                }
            });
        }
    }
};

// Details view common code for videos/exercises

var TopicItemNodeEditor = {
    init: function() {
        $('#details-view').find('input').change(TopicItemNodeEditor.handleChange);
    },

    handleChange: function() {
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
        if (unsavedChanges || TopicExerciseNodeEditor.unsavedChanges() || TopicUrlNodeEditor.unsavedChanges()) {
            $('#details-view .save-button').removeClass('disabled').addClass('green');
        } else {
            $('#details-view .save-button').addClass('disabled').removeClass('green');
        }
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
            TopicExerciseNodeEditor.applyChanges(attrs);
            TopicUrlNodeEditor.applyChanges(attrs);

            if (attrs != {}) {

                Throbber.show($("#details-view .save-button"), true);

				// We do special things on save because of the potential ID change
                var oldID = TopicNodeEditor.model.id;
                TopicNodeEditor.model.save(attrs, {
                    url: TopicNodeEditor.model.url(), // URL with the old slug value
                    success: function() {
                        TopicTreeEditor.handleChange(TopicNodeEditor.model, oldID);
                        Throbber.hide();
                    }
                });
            }

        } else if (action == 'copy_item') {
            TopicTopicNodeEditor.itemCopyBuffer = {
                type: 'copy',
                kind: kind,
                id: id,
                title: node.data.title,
                originalParent: parentModel.id,
            };

        } else if (action == 'cut_item') {
            TopicTopicNodeEditor.itemCopyBuffer = {
                type: 'cut',
                kind: kind,
                id: id,
                title: node.data.title,
                originalParent: parentModel.id,
                originalPosition: node.parent.childList.indexOf(node)
            };

        } else if (action == 'paste_after_item') {

            var new_position = node.parent.childList.indexOf(node)+1;

            if (!TopicTopicNodeEditor.itemCopyBuffer)
                return;

            if (TopicTopicNodeEditor.itemCopyBuffer.type == 'copy') {
                if (parentModel.id == TopicTopicNodeEditor.itemCopyBuffer.originalParent)
                    return;

                TopicTopicNodeEditor.finishAddExistingItem(TopicTopicNodeEditor.itemCopyBuffer.kind, TopicTopicNodeEditor.itemCopyBuffer.id, TopicTopicNodeEditor.itemCopyBuffer.title, node.parent, parentModel, new_position);

            } else if (TopicTopicNodeEditor.itemCopyBuffer.type == 'cut') {
                if (parentModel.id == TopicTopicNodeEditor.itemCopyBuffer.originalParent &&
                    new_position > TopicTopicNodeEditor.itemCopyBuffer.originalPosition)
                    new_position--;

                var data = {
                    kind: TopicTopicNodeEditor.itemCopyBuffer.kind,
                    id: TopicTopicNodeEditor.itemCopyBuffer.id,
                    new_parent_id: parentModel.id,
                    new_parent_pos: new_position
                }
                TopicTopicNodeEditor.moveItem(TopicTopicNodeEditor.itemCopyBuffer.originalParent, data);
            }

        } else if (action == 'remove_item') {
            data = {
                kind: kind,
                id: id
            };
            $.ajaxq('topics-admin', {
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
function arraysEqual(ar1, ar2) {
    if (ar1 && ar2) {
        if (!ar1 || !ar2)
            return false;
        if (ar1 < ar2 || ar1 > ar2)
            return false;
    }
    return true;
}

var TopicExerciseNodeEditor = {
    existingItemView: null,
    covers: null,
    prereqs: null,
    videos: null,

    unsavedChanges: function() {
        if (TopicExerciseNodeEditor.prereqs && TopicExerciseNodeEditor.covers) {
            return !(
                arraysEqual(TopicExerciseNodeEditor.prereqs, TopicNodeEditor.model.get('prereqs')) &&
                arraysEqual(TopicExerciseNodeEditor.covers, TopicNodeEditor.model.get('covers')) &&
                arraysEqual(TopicExerciseNodeEditor.videos, TopicNodeEditor.model.get('related_videos'))
            );
        }

        return false;
    },
    applyChanges: function(attrs) {
        if (TopicExerciseNodeEditor.prereqs && !arraysEqual(TopicExerciseNodeEditor.prereqs, TopicNodeEditor.model.get('prereqs')))
            attrs['prerequisites'] = TopicExerciseNodeEditor.prereqs;

        if (TopicExerciseNodeEditor.covers && !arraysEqual(TopicExerciseNodeEditor.covers, TopicNodeEditor.model.get('covers')))
            attrs['covers'] = TopicExerciseNodeEditor.covers;

        if (TopicExerciseNodeEditor.videos && !arraysEqual(TopicExerciseNodeEditor.videos, TopicNodeEditor.model.get('related_videos')))
            attrs['related_videos'] = TopicExerciseNodeEditor.videos;
    },

    updateCovers: function() {
        var html = '';
        _.each(TopicExerciseNodeEditor.covers, function(cover) {
            html += '<div>' + cover + ' (<a href="javascript: TopicExerciseNodeEditor.deleteCover(\'' + cover + '\');">remove</a>)</div>';
        });
        $("#exercise-covers-list").html(html);
    },
    chooseCover: function() {
        if (!TopicExerciseNodeEditor.existingItemView)
            TopicExerciseNodeEditor.existingItemView = new TopicAddExistingItemView();

        TopicExerciseNodeEditor.existingItemView.show('exercise', TopicExerciseNodeEditor.addCover);
    },
    addCover: function(kind, id, title) {
        if (id) {
            TopicExerciseNodeEditor.covers.push(id);
            TopicExerciseNodeEditor.updateCovers();
            TopicItemNodeEditor.handleChange();
        }
    },
    deleteCover: function(cover) {
        var idx = TopicExerciseNodeEditor.covers.indexOf(cover);
        if (idx >= 0) {
            TopicExerciseNodeEditor.covers.splice(idx, 1);
            TopicExerciseNodeEditor.updateCovers();
            TopicItemNodeEditor.handleChange();
        }
    },

    updatePrereqs: function() {
        var html = '';
        _.each(TopicExerciseNodeEditor.prereqs, function(prereq) {
            html += '<div>' + prereq + ' (<a href="javascript: TopicExerciseNodeEditor.deletePrereq(\'' + prereq + '\');">remove</a>)</div>';
        });
        $("#exercise-prereqs-list").html(html);
    },
    choosePrereq: function() {
        if (!TopicExerciseNodeEditor.existingItemView)
            TopicExerciseNodeEditor.existingItemView = new TopicAddExistingItemView();

        TopicExerciseNodeEditor.existingItemView.show('exercise', TopicExerciseNodeEditor.addPrereq);
    },
    addPrereq: function(kind, id, title) {
        if (id) {
            TopicExerciseNodeEditor.prereqs.push(id);
            TopicExerciseNodeEditor.updatePrereqs();
            TopicItemNodeEditor.handleChange();
        }
    },
    deletePrereq: function(prereq) {
        var idx = TopicExerciseNodeEditor.prereqs.indexOf(prereq);
        if (idx >= 0) {
            TopicExerciseNodeEditor.prereqs.splice(idx, 1);
            TopicExerciseNodeEditor.updatePrereqs();
            TopicItemNodeEditor.handleChange();
        }
    },

    updateVideos: function() {
        var html = '';
        _.each(TopicExerciseNodeEditor.videos, function(video) {
            html += '<div>' + video + ' (<a href="javascript: TopicExerciseNodeEditor.deleteVideo(\'' + video + '\');">remove</a>)</div>';
        });
        $("#exercise-videos-list").html(html);
    },
    chooseVideo: function() {
        if (!TopicExerciseNodeEditor.existingItemView)
            TopicExerciseNodeEditor.existingItemView = new TopicAddExistingItemView();

        TopicExerciseNodeEditor.existingItemView.show('video', TopicExerciseNodeEditor.addVideo);
    },
    addVideo: function(kind, id, title) {
        if (id) {
            TopicExerciseNodeEditor.videos.push(id);
            TopicExerciseNodeEditor.updateVideos();
            TopicItemNodeEditor.handleChange();
        }
    },
    deleteVideo: function(video) {
        var idx = TopicExerciseNodeEditor.videos.indexOf(video);
        if (idx >= 0) {
            TopicExerciseNodeEditor.videos.splice(idx, 1);
            TopicExerciseNodeEditor.updateVideos();
            TopicItemNodeEditor.handleChange();
        }
    },

    init: function() {
        // TomY TODO - related videos

        TopicItemNodeEditor.init();

        TopicExerciseNodeEditor.prereqs = TopicNodeEditor.model.get('prerequisites').slice(0);
        TopicExerciseNodeEditor.updatePrereqs();

        TopicExerciseNodeEditor.covers = TopicNodeEditor.model.get('covers').slice(0);
        TopicExerciseNodeEditor.updateCovers();

        TopicExerciseNodeEditor.videos = TopicNodeEditor.model.get('related_videos').slice(0);
        TopicExerciseNodeEditor.updateVideos();

        // Configure the search form
        $('#related-videos-input').placeholder();
        initAutocomplete("#related-videos-input", false, TopicExerciseNodeEditor.addVideo, true);
    },
    deinit: function() {
        TopicExerciseNodeEditor.prereqs = null;
        TopicExerciseNodeEditor.covers = null;
        TopicExerciseNodeEditor.videos = null;
    },
};

// Details view for videos

var TopicVideoNodeEditor = {
    init: function() {
        TopicItemNodeEditor.init();
    }
};

// Details view for external links

var TopicUrlNodeEditor = {
    tags: null,

    unsavedChanges: function() {
        if (TopicUrlNodeEditor.tags) {
            return !(
                arraysEqual(TopicUrlNodeEditor.tags, TopicNodeEditor.model.get('tags'))
            );
        }

        return false;
    },
    applyChanges: function(attrs) {
        if (TopicUrlNodeEditor.tags && !arraysEqual(TopicUrlNodeEditor.tags, TopicNodeEditor.model.get('tags')))
            attrs['tags'] = TopicUrlNodeEditor.tags;
    },

    updateTags: function() {
        var html = '';
        _.each(TopicUrlNodeEditor.tags, function(tag) {
            html += '<div>' + tag + ' (<a href="javascript: TopicUrlNodeEditor.deleteTag(\'' + tag + '\');">remove</a>)</div>';
        });
        $("#url-tags-list").html(html);
    },
    addTag: function() {
        var tag = $('#url-tag-add').val();
        var idx = TopicUrlNodeEditor.tags.indexOf(tag);
        if (tag && idx < 0) {
            TopicUrlNodeEditor.tags.push(tag);
            TopicUrlNodeEditor.updateTags();
            TopicItemNodeEditor.handleChange();
        }

        $('#url-tag-add').val('');
    },
    deleteTag: function(tag) {
        var idx = TopicUrlNodeEditor.tags.indexOf(tag);
        if (idx >= 0) {
            TopicUrlNodeEditor.tags.splice(idx, 1);
            TopicUrlNodeEditor.updateTags();
            TopicItemNodeEditor.handleChange();
        }
    },

    init: function() {
        TopicItemNodeEditor.init();

        TopicUrlNodeEditor.tags = TopicNodeEditor.model.get('tags').slice(0);
        TopicUrlNodeEditor.updateTags();
    },
    deinit: function() {
        TopicUrlNodeEditor.tags = null;
    }
};

// Add existing video/exercise dialog box

var TopicAddExistingItemView = Backbone.View.extend({
    template: Templates.get( "topicsadmin.add-existing-item" ),
    loaded: false,
    type: '',
    results: {},
    callback: null,

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

    show: function(type, callback) {
        $(this.el).modal({
            keyboard: true,
            backdrop: true,
            show: true
        });

        if (type != this.type)
            this.loaded = false;
        this.type = type;
        this.callback = callback;

        $(this.el).find('.title').html('Choose ' + type + ':');

        if (!this.loaded) {
            this.showRecent();
        }
    },

    showResults: function(json) {
        var html = '';
        var self = this;
        this.results = {};
        _.each(json, function(item) {
            if (self.type == 'video') {
                html += '<option value="' + item.readable_id + '">' + item.title + '</option>';
                self.results[item.readable_id] = item.title;
            } else {
                html += '<option value="' + item.name + '">' + item.display_name + '</option>';
                self.results[item.name] = item.display_name;
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
            readable_id: '_',
            name: '_',
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
        if (!itemID || itemID == '_')
            return;

        this.hide();

        var kind;
        if (this.type == 'video')
            kind = 'Video';
        else
            kind = 'Exercise';

        this.callback(kind, itemID, this.results[itemID], null, null, -1);
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
                TopicTopicNodeEditor.finishAddExistingItem('Exercise', name, exercise.get('display_name'), null, null, -1);
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
        $(this.el).find('input[name="youtube_id"]').val('');
        $(this.el).find('.create-video-preview').html("Enter a YouTube ID to look up a video.");
        $(self.el).find('.ok_button').addClass('disabled').removeClass('green');
    },

    createVideo: function() {
        if (!this.youtubeID)
            return;

        var video = new Video({ youtube_id: this.youtubeID });

        video.save({}, {
            success: function(model) {
                TopicTopicNodeEditor.finishAddExistingItem('Video', model.get('readable_id'), model.get('title'), null, null, -1);
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

// Add a new url dialog box

var TopicCreateUrlView = Backbone.View.extend({
    template: Templates.get( "topicsadmin.create-url" ),

    initialize: function() {
        this.render();
    },

    events: {
        'click .ok_button': 'createUrl'
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

        $(this.el).find('input[name="url"]').val('');
    },

    createUrl: function() {
        var url = $(this.el).find('input[name="url"]').val();
        var title = $(this.el).find('input[name="title"]').val();
        var urlObject = new ExternalURL({ url: url, title: title });

        urlObject.save({}, {
            success: function(model) {
                TopicTopicNodeEditor.finishAddExistingItem('Url', model.id, model.get('title'), null, null, -1);
            }
        });
        this.hide();
    },

    hide: function() {
        return $(this.el).modal('hide');
    }
});

// View versions list

var TopicVersionListView = Backbone.View.extend({
    template: Templates.get( "topicsadmin.list-versions" ),
    templateItem: Templates.get( "topicsadmin.list-versions-item" ),

    initialize: function() {
        this.render();
    },

    events: {
    },

    render: function() {
        this.el = $(this.template({})).appendTo(document.body).get(0);
        this.delegateEvents();
        return this;
    },

    show: function(type) {
        $(this.el).modal({
            keyboard: true,
            backdrop: true,
            show: true
        });

        var self = this;
        getTopicVersionList().fetch({
            success: function() {
                var html = '';
                _.each(getTopicVersionList().models, function(model) {
                    html += self.templateItem(model.toJSON());
                });
                $('.version-list', self.el).html(html);
            }
        });
        return this;
    },

    hide: function() {
        return $(this.el).modal('hide');
    }
});
