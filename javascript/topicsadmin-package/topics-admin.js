// Creates & handles events for the topic tree

var debugNodeIDs = false;

var TopicTreeEditor = {

    tree: null,
    boundList: [],
    maxProgressLength: 0,
    currentVersion: null,
    versionEditTemplate: Templates.get("topicsadmin.edit-version"),
    searchView: null,

    // Initialize the Dynatree view of the given TopicVersion's topic tree.
    init: function(version) {
        var topicTree = version.getTopicTree();
        this.currentVersion = version;


        // Attach the dynatree widget to an existing <div id="tree"> element
        // and pass the tree options as an argument to the dynatree() function:
        $("#topic_tree").dynatree({
            imagePath: "/images/",

            onActivate: function(node) {
                KAConsole.log("Activated: ", node);

                TopicTreeEditor.NodeEditor.init();

                if (node.data.kind == "Topic" && node.data.id != "root") {
                    topicTree.fetchByID(node.data.id, TopicTreeEditor.NodeEditor.initModel, [node]);
                } else if (node.data.kind == "Video") {
                    getVideoList().fetchByID(node.data.id, TopicTreeEditor.NodeEditor.initModel, [node]);
                } else if (node.data.kind == "Exercise") {
                    getExerciseList().fetchByID(node.data.id, TopicTreeEditor.NodeEditor.initModel, [node]);
                } else if (node.data.kind == "Url") {
                    getUrlList().fetchByID(node.data.id, TopicTreeEditor.NodeEditor.initModel, [node]);
                } else {
                    $("#details-view").html("");
                }
            },

            onCreate: function(node, span) {
                if (node.data.kind == "Topic") {
                    $(span).contextMenu({menu: "topic_context_menu"}, function(action, el, pos) {
                        topicTree.fetchByID(node.data.id, function() {
                            TopicTreeEditor.TopicEditor.handleAction(action, node, this, topicTree.get(node.parent.data.id));
                        });
                    });
                }
                if (_.include(["Video", "Exercise", "Url"], node.data.kind)) {
                    $(span).contextMenu({menu: "item_context_menu"}, function(action, el, pos) {
                        TopicTreeEditor.ItemEditor.handleAction(action, node, node.data.kind, node.data.id, topicTree.get(node.parent.data.id));
                    });
                }
            },

            onExpand: function(flag, node) {
                if (flag) {
                    node.activate();
                }
            },

            onLazyRead: function(node) {
                if (node.data.key == "UnrefContent") {
                    $.ajaxq("topics-admin", {
                        url: "/api/v1/topicversion/" + TopicTreeEditor.currentVersion.get("number") + "/unused_content",
                        success: function(json) {
                            node.removeChildren();

                            childNodes = [];
                            _.each(json, function(item) {
                                var childWrapper = new TopicChild(item);
                                childNodes.push(TopicTreeEditor.createChild(childWrapper));
                            });
                            node.addChild(childNodes);
                        },
                        error: TopicTreeEditor.handleError
                    });
                } else {
                    topicTree.fetchByID(node.data.id, TopicTreeEditor.refreshTreeNode);
                }
            },

            dnd: {
                onDragStart: function(node) {
                    return TopicTreeEditor.currentVersion.get("edit");
                },

                onDragEnter: function(node, sourceNode) {
                    if (node.data.key == "UnrefContent" ||
                        node.parent.data.key == "UnrefContent") {
                        return [];
                    }

                    if (node.data.kind != "Topic") {
                        return ["before", "after"];
                    }

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

                    if (oldParent.data.key == "UnrefContent") {
                        TopicTreeEditor.TopicEditor.finishAddExistingItem(sourceNode.data.kind, sourceNode.data.id, sourceNode.data.title, newParent, topicTree.get(newParent.data.id), newParent.childList.indexOf(sourceNode));
                    } else {
                        var data = {
                            kind: sourceNode.data.kind,
                            id: sourceNode.data.id,
                            new_parent_id: newParent.data.id,
                            new_parent_pos: newParent.childList.indexOf(sourceNode)
                        };
                        TopicTreeEditor.TopicEditor.moveItem(oldParent.data.id, data); 
                    }
                }
            },

            children: [ {
                    title: "Loading...",
                    key: "Topic/root",
                    id: "root",
                    kind: "Topic",
                    isFolder: true,
                    isLazy: true,
                    icon: "topictree-icon-small.png"
                }, {
                    title: "Unreferenced Content",
                    key: "UnrefContent",
                    id: "",
                    kind: "",
                    isFolder: true,
                    isLazy: true,
                    icon: "topictree-icon-small.png"
            } ]
        });
        TopicTreeEditor.tree = $("#topic_tree").dynatree("getTree");
        $("#topic_tree").bind("mousedown", function(e) { e.preventDefault(); });

        $("#details-view").html("");

        $("#topicversion-editor")
            .html(TopicTreeEditor.versionEditTemplate(version.toJSON()))
            .delegate( "input[type=\"text\"]", "change", function() {
                    var field = $(this).attr("name");
                    if (field) {
                        var value = $(this).val();

                        var attrs = {};
                        attrs[field] = value;

                        version.save(attrs);
                    }
                } )
            .delegate( "a.set-default", "click", TopicTreeEditor.setTreeDefault )
            .delegate( "a.show-versions", "click", TopicTreeEditor.showVersionList );

        $("#topictree-queue-progress-bar").progressbar({ value: 0, disable: true });
        $("#topictree-queue-progress-text").html("");

        if (!this.searchView) {
            this.searchView = new TopicTreeEditor.SearchView();
            $(this.searchView.el).appendTo(document.body);
        }

        var self = this;
        $(window).resize(function() { self.resize(); } );
        this.resize();

        // Get the data for the topic tree (may fire callbacks immediately)

        topicTree.bind("add", this.treeUpdate, topicTree);
        topicTree.bind("remove", this.treeUpdate, topicTree);
        topicTree.bind("clear", this.treeUpdate, topicTree);

        var root = topicTree.getRoot();
        root.bind("change", this.refreshTreeNode);
        if (root.__inited) {
            this.refreshTreeNode.call(null, root);
        }

        this.updateProgressBar();
    },

    updateProgressBar: function() {
        if (document.ajaxq && document.ajaxq.q["topics-admin"] &&
            document.ajaxq.q["topics-admin"].length > 0) {
            $("#topictree-queue-progress-bar").progressbar("enable");

            var remaining = document.ajaxq.q["topics-admin"].length;
            if (TopicTreeEditor.maxProgressLength < remaining) {
                TopicTreeEditor.maxProgressLength = remaining;
            }

            var progress_percentage = (1 - (remaining / TopicTreeEditor.maxProgressLength)) * 100;
            var progress = TopicTreeEditor.maxProgressLength - remaining + 1;

            $("#topictree-queue-progress-bar").progressbar("value", progress_percentage);
            $("#topictree-queue-progress-text").html("Updating (" + progress + " / " + TopicTreeEditor.maxProgressLength + ")");

        } else {
            if (TopicTreeEditor.maxProgressLength > 0) {
                $("#topictree-queue-progress-text").html("Done updating.");
                $("#topictree-queue-progress-bar").progressbar("value", 100);
                TopicTreeEditor.maxProgressLength = 0; // 1 second delay before we wipe the progress
            } else {
                $("#topictree-queue-progress-bar").progressbar({ value: 0, disable: true });
            }
        }

        setTimeout(TopicTreeEditor.updateProgressBar, 1000);
    },

    resize: function() {
        var containerHeight = $(window).height();
        var yTopPadding = $("#topic_tree").offset().top;
        var newHeight = containerHeight - (yTopPadding + 42);

        $("#topic_tree").height(newHeight);
        $("#details-view").height(newHeight);

        $(this.searchView.el).offset($("#topic_tree").offset());
    },

    createChild: function(child) {
        var iconTable = {
            Topic: "leaf-icon-small.png",
            Video: "video-camera-icon-full-small.png",
            Exercise: "exercise-icon-small.png",
            Url: "link-icon-small.png"
        };
        var data = {
            title: child.title,
            key:  child.kind + "/" + child.id,
            id: child.id,
            kind: child.kind,
            icon: iconTable[child.kind]
        };
        if (debugNodeIDs) {
            data.title += " [(" + child.id + ")]";
        }
        if (child.kind == "Topic") {
            data.isFolder = true;
            data.isLazy = true;
            if (child.hide) {
                data.addClass = "hidden-topic";
                data.title = child.title + " [Hidden]";
            }
        }
        return data;
    },

    refreshTreeNode: function(model) {
        node = TopicTreeEditor.tree.getNodeByKey(model.get("kind") + "/" + model.id);
        if (!node) {
            return;
        }

        KAConsole.log("refreshing " + model.id);

        if (debugNodeIDs) {
            node.setTitle(model.get("title") + " [" + model.id + "]");
        } else {
            node.setTitle(model.get("title"));
        }

        node.removeChildren();
        if (model.get("children")) {
            childNodes = [];
            _.each(model.get("children"), function(child) {
                childNodes.push(TopicTreeEditor.createChild(child));
            });
            node.addChild(childNodes);
        }

        if (model.id == "root") {
            node.expand();
        }
    },

    handleChange: function(model, oldID) {
        var modelWrapper = TopicChild(model);

        KAConsole.log("Model of type " + modelWrapper.kind + " changed ID: " + oldID + " -> " + model.id);

        TopicTreeEditor.currentVersion.getTopicTree().each(function(topic) {
            var found = false;
            var children = _.map(topic.get("children"), function(child) {
                if (child.kind == modelWrapper.kind && child.id == oldID) {
                    var new_child = {
                        id: model.id,
                        kind: modelWrapper.kind,
                        title: modelWrapper.title,
                        hide: child.hide
                    };

                    found = true;

                    return new_child;
                } else {
                    return child;
                }
            });
            if (found) {
                topic.set({children: children});
            }
        });
    },

    // Called with TopicTree as "this"
    treeUpdate: function() {
        this.each(function(childModel) {
            var found = false;
            _.each(TopicTreeEditor.boundList, function(childId) {
                if (childId == childModel.id) {
                    found = true;
                }
            });
            if (!found) {
                //KAConsole.log("Binding: " + childModel.id);
                childModel.bind("change", TopicTreeEditor.refreshTreeNode);
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
        $.ajaxq("topics-admin", {
            url: "/api/v1/topicversion/edit/setdefault",
            success: function() {
                hideGenericMessageBox();
                popupGenericMessageBox({
                    title: "Topic tree published",
                    message: "Topic tree has been published to the live site.",
                    buttons: null
                });
            },
            error: TopicTreeEditor.handleError
        });
    },

    showVersionList: function() {
        this.versionListView = new TopicTreeEditor.VersionListView().show();
    },

    editVersion: function(versionNumber) {
        if (this.versionListView) {
            this.versionListView.hide();
        }

        version = getTopicVersionList().get(versionNumber);
        if (version) {
            version.getTopicTree().reset();
            this.init(version);
        }
    },

    handleError: function() {
        popupGenericMessageBox({
            title: "Server error",
            message: "There has been a server error. The topic tree will now refresh.",
            buttons: [
                { title: "OK", action: function() { hideGenericMessageBox(); TopicTreeEditor.editVersion(TopicTreeEditor.currentVersion.get("number")); } }
            ]
        });
    },

    // Details view common code

    NodeEditor: {

        node: null,
        model: null,
        parentModel: null,
        modelKind: null,
        template: null,

        init: function(kind, model, parentModel) {
            _.bindAll(this);
            
            if (this.model) {
                this.model.unbind("change", this.render);
            }

            $("#details-view").html("<div style=\"left: 350px; position: relative; width: 10px;\"><div class=\"dialog-progress-bar\"></div></div>");
            $("#details-view .dialog-progress-bar").progressbar({ enable: true, value: 100 });
        }, 

        initModel: function(model, node) {
            this.node = node;
            this.modelKind = model.get('kind');
            this.model = model;
            this.parentModel = TopicTreeEditor.currentVersion.getTopicTree().get(node.parent.data.id);
            this.template = Templates.get("topicsadmin.edit-" + model.get('kind').toLowerCase());

            this.render();

            model.bind("change", this.render);
        },

        render: function() {
            js = this.model.toJSON();
            html = this.template({version: TopicTreeEditor.currentVersion.toJSON(), model: js});

            $("#details-view").html(html);

            TopicTreeEditor.ExerciseEditor.deinit();
            TopicTreeEditor.UrlEditor.deinit();

            if (this.modelKind == "Topic") {
                TopicTreeEditor.TopicEditor.init();
            } else if (this.modelKind == "Exercise") {
                TopicTreeEditor.ExerciseEditor.init();
            } else if (this.modelKind == "Video") {
                TopicTreeEditor.VideoEditor.init();
            } else if (this.modelKind == "Url") {
                TopicTreeEditor.UrlEditor.init();
            } 

            $( "#details-view a.item-action" ).click(function() {
                var action = $( this ).attr( "data-id" );
                TopicTreeEditor.ItemEditor.handleAction( action );
            });
        }
    },

    // Details view & editing functions for topics

    TopicEditor: {
        existingItemView: null,
        newExerciseView: null,
        newVideoView: null,
        newUrlView: null,
        contextNode: null,
        contextModel: null,
        itemCopyBuffer: null,

        init: function() {
            _.bindAll(this);
            this.nodeEditor = TopicTreeEditor.NodeEditor;

            if ( TopicTreeEditor.currentVersion.get( "edit" ) ) {
                $( "#details-view" )
                    .find( "input" )
                        .change( function() {
                            var field = $(this).attr( "name" );
                            if (field) {
                                var value = ( this.type == "checkbox" ) ?  $( this ).is( ":checked" ) : $( this ).val();
                                var attrs = {};
                                var oldID = this.nodeEditor.model.id;
                                var self = this;
                                attrs[field] = value;

                                // We do special things on save because of the potential ID change
                                this.nodeEditor.model.save( attrs, {
                                    url: self.nodeEditor.model.url(), // URL with the old slug value
                                    success: function() { TopicTreeEditor.handleChange( self.nodeEditor.model, oldID ); }
                                });
                            }
                        })
                        .end()
                    .find( "#add-tag-button" )
                        .click( this.addTag )
                        .end();
            }
        },

        addTag: function() {
            var tag = $( "#add-tag" ).val();

            if ( tag ) {
                var tags = this.nodeEditor.model.get( "tags" ).slice( 0 );
 
                tags.push( tag );
                this.nodeEditor.model.set({tags: tags}); // This triggers a NodeEditor.render()
                this.nodeEditor.model.save();
            }
        },
        deleteTag: function(tag) {
            var tags = this.nodeEditor.model.get( "tags" ).slice( 0 );

            var idx = tags.indexOf(tag);
            if ( idx >= 0 ) {
                tags.splice( idx, 1 );
                this.nodeEditor.model.set({tags: tags}); // This triggers a NodeEditor.render()
                this.nodeEditor.model.save();
            }
        },

        handleAction: function(action, node, model, parentModel) {
            node = node || this.nodeEditor.node;
            model = model || this.nodeEditor.model;
            parentModel = parentModel || this.nodeEditor.parentModel;

            this.contextNode = node;
            this.contextModel = model;

            if (action == "add_new_topic") {
                var topic = new Topic();
                KAConsole.log("Creating new topic...");
                topic.save({}, {
                    success: function() {
                        KAConsole.log("Created new topic:", topic.id);
                        var data = {
                            kind: "Topic",
                            id: topic.id,
                            pos: model.get("children").length
                        };
                        $.ajaxq("topics-admin", {
                            url: "/api/v1/topic/" + model.id + "/addchild",
                            type: "POST",
                            data: data,
                            success: function(json) {
                                KAConsole.log("Added topic successfully.");
                                model.set(json);

                                node.expand();
                                node.getChildren()[data.pos].activate();
                            },
                            error: TopicTreeEditor.handleError
                        });
                    }
                });

            } else if (action == "add_new_video") {
                this.newVideoView = this.newVideoView || new TopicTreeEditor.CreateVideoView();
                this.newVideoView.show();

            } else if (action == "add_existing_video") {
                this.existingItemView = this.existingItemView || new TopicTreeEditor.AddExistingItemView();
                this.existingItemView.show("video", this.finishAddExistingItem);

            } else if (action == "add_new_exercise") {
                this.newExerciseView = this.newExerciseView || new TopicTreeEditor.CreateExerciseView();
                this.newExerciseView.show();

            } else if (action == "add_existing_exercise") {
                this.existingItemView = this.existingItemView || new TopicTreeEditor.AddExistingItemView();
                this.existingItemView.show("exercise", this.finishAddExistingItem);

            } else if (action == "add_new_url") {
                this.newUrlView = this.newUrlView || new TopicTreeEditor.CreateUrlView();
                this.newUrlView.show();

            } else if (action == "paste_item") {

                if (!this.itemCopyBuffer) {
                    return;
                }

                if (this.itemCopyBuffer.type == "copy") {
                    this.finishAddExistingItem(this.itemCopyBuffer.kind, this.itemCopyBuffer.id, this.itemCopyBuffer.title, null, null, -1);

                } else if (this.itemCopyBuffer.type == "cut") {
                    var moveData = {
                        kind: this.itemCopyBuffer.kind,
                        id: this.itemCopyBuffer.id,
                        new_parent_id: model.id,
                        new_parent_pos: model.get("children").length
                    };
                    this.moveItem(this.itemCopyBuffer.originalParent, moveData);
                }

            } else if (action == "delete_topic") {
                var deleteData = {
                    kind: "Topic",
                    id: model.id
                };
                $.ajaxq("topics-admin", {
                    url: "/api/v1/topic/" + parentModel.id + "/deletechild",
                    type: "POST",
                    data: deleteData,
                    success: function(json) {
                        parentModel.removeChild("Topic", model.id);
                    },
                    error: TopicTreeEditor.handleError
                });
            }
        },

        finishAddExistingItem: function(kind, id, title, node, model, pos) {

            model = model || this.contextModel;
            node = node || this.contextNode;

            if (pos < 0) {
                pos = model.get("children").length;
            }

            KAConsole.log("Adding " + kind + " " + id + " to Topic " + model.get("title"));

            var newChild = {
                kind: kind,
                id: id,
                title: title
            };
            children = model.get("children").slice(0);
            children.splice(pos, 0, newChild);
            model.set({ children: children });

            node.expand();
            node.getChildren()[pos].activate();

            var data = {
                kind: kind,
                id: id,
                pos: pos
            };
            $.ajaxq("topics-admin", {
                url: "/api/v1/topic/" + model.id + "/addchild",
                type: "POST",
                data: data,
                success: function(json) {
                    KAConsole.log("Added item successfully.");
                },
                error: TopicTreeEditor.handleError
            });
        },


        moveItem: function(oldParentID, moveData) {
            // Apply the change to the model data first
            child = TopicTreeEditor.currentVersion.getTopicTree().get(oldParentID).removeChild(moveData.kind, moveData.id);
            new_parent = TopicTreeEditor.currentVersion.getTopicTree().fetchByID(moveData.new_parent_id, function(model) {
                model.addChild(child, moveData.new_parent_pos);

                parent_node = TopicTreeEditor.tree.getNodeByKey("Topic/" + moveData.new_parent_id);
                parent_node.expand();
                parent_node.getChildren()[moveData.new_parent_pos].activate();

                $.ajaxq("topics-admin", {
                    url: "/api/v1/topic/" + oldParentID + "/movechild",
                    type: "POST",
                    data: moveData,
                    success: function() {
                    },
                    error: TopicTreeEditor.handleError
                });
            });
        }
    },

    // Details view common code for videos/exercises

    ItemEditor: {
        init: function() {
            this.nodeEditor = TopicTreeEditor.NodeEditor;
            this.topicEditor = TopicTreeEditor.TopicEditor;

            _.bindAll(this);

            $("#details-view").find("input").change(this.handleChange);
        },

        handleChange: function() {
            var self = this;
            unsavedChanges = false;
            $("#details-view input[type=\"text\"]")
                .add("#details-view input[type=\"radio\"]:checked")
                .each(function() {
                    var field = $(this).attr("name");
                    if (field) {
                        if (String(self.nodeEditor.model.get(field)) != $(this).val()) {
                            unsavedChanges = true;
                        }
                    }
                });
            if (unsavedChanges || TopicTreeEditor.ExerciseEditor.unsavedChanges() || TopicTreeEditor.UrlEditor.unsavedChanges()) {
                $("#details-view .save-button").removeClass("disabled").addClass("green");
            } else {
                $("#details-view .save-button").addClass("disabled").removeClass("green");
            }
        },

        handleAction: function(action, node, kind, id, parentModel) {
            kind = kind || this.nodeEditor.modelKind;
            id = id || this.nodeEditor.model.id;
            parentModel = parentModel || this.nodeEditor.parentModel;

            if (action == "save") {
                var attrs = {};
                $("#details-view input[type=\"text\"]")
                    .add("#details-view input[type=\"radio\"]:checked")
                    .each(function() {
                        var field = $(this).attr("name");
                        if (field) {
                            if (String(this.nodeEditor.model.get(field)) != $(this).val()) {
                                attrs[field] = $(this).val();
                            }
                        }
                    });
                TopicTreeEditor.ExerciseEditor.applyChanges(attrs);
                TopicTreeEditor.UrlEditor.applyChanges(attrs);

                if (attrs != {}) {

                    Throbber.show($("#details-view .save-button"), true);

                    // We do special things on save because of the potential ID change
                    var oldID = this.nodeEditor.model.id;
                    var self = this;
                    this.nodeEditor.model.save(attrs, {
                        url: self.nodeEditor.model.url(), // URL with the old slug value
                        success: function() {
                            TopicTreeEditor.handleChange(this.nodeEditor.model, oldID);
                            Throbber.hide();
                        }
                    });
                }

            } else if (action == "copy_item") {
                this.topicEditor.itemCopyBuffer = {
                    type: "copy",
                    kind: kind,
                    id: id,
                    title: node.data.title,
                    originalParent: parentModel.id
                };

            } else if (action == "cut_item") {
                this.topicEditor.itemCopyBuffer = {
                    type: "cut",
                    kind: kind,
                    id: id,
                    title: node.data.title,
                    originalParent: parentModel.id,
                    originalPosition: node.parent.childList.indexOf(node)
                };

            } else if (action == "paste_after_item") {

                var new_position = _.indexOf(node.parent.childList, node) + 1;

                if (!this.topicEditor.itemCopyBuffer) {
                    return;
                }

                if (this.topicEditor.itemCopyBuffer.type == "copy") {
                    if (parentModel.id == this.topicEditor.itemCopyBuffer.originalParent) {
                        return;
                    }

                    this.topicEditor.finishAddExistingItem(this.topicEditor.itemCopyBuffer.kind, this.topicEditor.itemCopyBuffer.id, this.topicEditor.itemCopyBuffer.title, node.parent, parentModel, new_position);

                } else if (this.topicEditor.itemCopyBuffer.type == "cut") {
                    if (parentModel.id == this.topicEditor.itemCopyBuffer.originalParent &&
                        new_position > this.topicEditor.itemCopyBuffer.originalPosition) {
                        new_position--;
                    }

                    var moveData = {
                        kind: this.topicEditor.itemCopyBuffer.kind,
                        id: this.topicEditor.itemCopyBuffer.id,
                        new_parent_id: parentModel.id,
                        new_parent_pos: new_position
                    };
                    this.topicEditor.moveItem(this.topicEditor.itemCopyBuffer.originalParent, moveData);
                }

            } else if (action == "remove_item") {
                var deleteData = {
                    kind: kind,
                    id: id
                };
                $.ajaxq("topics-admin", {
                    url: "/api/v1/topic/" + parentModel.id + "/deletechild",
                    type: "POST",
                    data: deleteData,
                    success: function(json) {
                        parentModel.removeChild(kind, id);
                    },
                    error: TopicTreeEditor.handleError
                });

            }
        }
    },

    // Utility function for comparing arrays of strings only (type coercion/null/undefined values are not relevant)
    arraysEqual: function(ar1, ar2) {
        return !(ar1 < ar2 || ar1 > ar2);
    },

    // Details view for exercises

    ExerciseEditor: {
        existingItemView: null,
        covers: null,
        prereqs: null,
        videos: null,

        init: function() {
            this.nodeEditor = TopicTreeEditor.NodeEditor;
            this.itemEditor = TopicTreeEditor.ItemEditor;

            _.bindAll(this);

            this.itemEditor.init();

            this.prereqs = this.nodeEditor.model.get("prerequisites").slice(0);
            this.updatePrereqs();

            this.covers = this.nodeEditor.model.get("covers").slice(0);
            this.updateCovers();

            this.videos = (this.nodeEditor.model.get("related_videos") || []).slice(0);
            this.updateVideos();
        },
        deinit: function() {
            this.prereqs = null;
            this.covers = null;
            this.videos = null;
        },

        unsavedChanges: function() {
            if (this.prereqs && this.covers) {
                return !(
                    TopicTreeEditor.arraysEqual(this.prereqs, this.nodeEditor.model.get("prereqs")) &&
                    TopicTreeEditor.arraysEqual(this.covers, this.nodeEditor.model.get("covers")) &&
                    TopicTreeEditor.arraysEqual(this.videos, this.nodeEditor.model.get("related_videos"))
                );
            }

            return false;
        },
        applyChanges: function(attrs) {
            if (this.prereqs && !TopicTreeEditor.arraysEqual(this.prereqs, this.nodeEditor.model.get("prereqs"))) {
                attrs.prerequisites = this.prereqs;
            }

            if (this.covers && !TopicTreeEditor.arraysEqual(this.covers, this.nodeEditor.model.get("covers"))) {
                attrs.covers = this.covers;
            }

            if (this.videos && !TopicTreeEditor.arraysEqual(this.videos, this.nodeEditor.model.get("related_videos"))) {
                attrs.related_videos = this.videos;
            }
        },

        updateCovers: function() {
            var elements = [];
            _.each(this.covers, function(cover) {
                elements.push(
                    $("<div>" + cover + " <a href=\"javascript:\">(remove)</a></div>")
                        .delegate("a", "click", function() { this.deleteCover(cover); })
                );
            });
            $("#exercise-covers-list").children().remove();
            _.each(elements, function(element) { element.appendTo("#exercise-covers-list"); });
        },
        chooseCover: function() {
            this.existingItemView = this.existingItemView || new TopicTreeEditor.AddExistingItemView();
            this.existingItemView.show("exercise", this.addCover);
        },
        addCover: function(kind, id, title) {
            if (id) {
                this.covers.push(id);
                this.updateCovers();
                this.itemEditor.handleChange();
            }
        },
        deleteCover: function(cover) {
            var idx = this.covers.indexOf(cover);
            if (idx >= 0) {
                this.covers.splice(idx, 1);
                this.updateCovers();
                this.itemEditor.handleChange();
            }
        },

        updatePrereqs: function() {
            var elements = [];
            _.each(this.prereqs, function(prereq) {
                elements.push(
                    $("<div>" + prereq + " <a href=\"javascript:\">(remove)</a></div>")
                        .delegate("a", "click", function() { this.deletePrereq(prereq); })
                );
            });
            $("#exercise-prereqs-list").children().remove();
            _.each(elements, function(element) { element.appendTo("#exercise-prereqs-list"); });
        },
        choosePrereq: function() {
            this.existingItemView = this.existingItemView || new TopicTreeEditor.AddExistingItemView();
            this.existingItemView.show("exercise", this.addPrereq);
        },
        addPrereq: function(kind, id, title) {
            if (id) {
                this.prereqs.push(id);
                this.updatePrereqs();
                this.itemEditor.handleChange();
            }
        },
        deletePrereq: function(prereq) {
            var idx = this.prereqs.indexOf(prereq);
            if (idx >= 0) {
                this.prereqs.splice(idx, 1);
                this.updatePrereqs();
                this.itemEditor.handleChange();
            }
        },

        updateVideos: function() {
            var elements = [];
            _.each(this.videos, function(video) {
                elements.push(
                    $("<div>" + video + " <a href=\"javascript:\">(remove)</a></div>")
                        .delegate("a", "click", function() { this.deleteVideo(video); })
                );
            });
            $("#exercise-videos-list").children().remove();
            _.each(elements, function(element) { element.appendTo("#exercise-videos-list"); });
        },
        chooseVideo: function() {
            this.existingItemView = this.existingItemView || new TopicTreeEditor.AddExistingItemView();
            this.existingItemView.show("video", this.addVideo);
        },
        addVideo: function(kind, id, title) {
            if (id) {
                this.videos.push(id);
                this.updateVideos();
                this.itemEditor.handleChange();
            }
        },
        deleteVideo: function(video) {
            var idx = this.videos.indexOf(video);
            if (idx >= 0) {
                this.videos.splice(idx, 1);
                this.updateVideos();
                this.itemEditor.handleChange();
            }
        }
    },

    // Details view for videos

    VideoEditor: {
        init: function() {
            this.itemEditor = TopicTreeEditor.ItemEditor;

            _.bindAll(this);

            this.itemEditor.init();
        }
    },

    // Details view for external links

    UrlEditor: {
        tags: null,

        init: function() {
            this.nodeEditor = TopicTreeEditor.NodeEditor;
            this.itemEditor = TopicTreeEditor.ItemEditor;

            _.bindAll(this);

            this.itemEditor.init();

            this.tags = this.nodeEditor.model.get("tags").slice(0);
            this.updateTags();

            $( "#add-tag-button" ).click( this.addTag );
        },
        deinit: function() {
            this.tags = null;
        },

        unsavedChanges: function() {
            if (this.tags) {
                return !(
                    TopicTreeEditor.arraysEqual(this.tags, this.nodeEditor.model.get("tags"))
                );
            }

            return false;
        },
        applyChanges: function(attrs) {
            if (this.tags && !TopicTreeEditor.arraysEqual(this.tags, this.nodeEditor.model.get("tags"))) {
                attrs.tags = this.tags;
            }
        },

        updateTags: function() {
            var elements = [];
            var self = this;
            _.each( this.tags, function( tag ) {
                elements.push(
                    $("<div>" + tag + " <a href=\"javascript:\">(remove)</a></div>")
                        .delegate( "a", "click", function() { self.deleteTag(tag); } )
                );
            });
            $("#url-tags-list").children().remove();
            _.each( elements, function( element ) { element.appendTo("#url-tags-list"); } );
        },
        addTag: function() {
            var tag = escape($("#url-tag-add").val());
            var idx = this.tags.indexOf(tag);
            if (tag && idx < 0) {
                this.tags.push(tag);
                this.updateTags();
                this.itemEditor.handleChange();
            }

            $("#url-tag-add").val("");
        },
        deleteTag: function(tag) {
            var idx = this.tags.indexOf(tag);
            if (idx >= 0) {
                this.tags.splice(idx, 1);
                this.updateTags();
                this.itemEditor.handleChange();
            }
        }
    },

    // Add existing video/exercise dialog box

    AddExistingItemView: Backbone.View.extend({
        template: Templates.get( "topicsadmin.add-existing-item" ),
        loaded: false,
        type: "",
        results: {},
        callback: null,

        initialize: function() {
            this.render();
        },

        events: {
            "click .do-search": "doSearch",
            "click .show-recent": "showRecent",
            "click .ok-button": "selectItem"
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

            if (type != this.type) {
                this.loaded = false;
            }
            this.type = type;
            this.callback = callback;

            $(this.el).find(".title").html("Choose " + type + ":");

            if (!this.loaded) {
                this.showRecent();
            }
        },

        showResults: function(json) {
            var elements = [];
            var self = this;
            this.results = {};
            _.each(json, function(item) {
                if (self.type == "video") {
                    elements.push( $( '<option value="' + item.readable_id + '"' + item.title + '</option>' ) );
                    self.results[ item.readable_id ] = item.title;
                } else {
                    elements.push( $( '<option value="' + item.name + '"' + item.display_name + '</option>' ) );
                    self.results[ item.name ] = item.display_name;
                }
            });

            var resultsElemenet = $( "select.search-results", this.el );
            resultsElement.html( "" );
            _.each( elements, function( element ) { element.appendTo( resultsElement.get(0) ); } );
        },

        showRecent: function() {
            var self = this;

            if (this.type == "video") {
                $(this.el).find(".search-description").html("Most recent videos:");
            } else {
                $(this.el).find(".search-description").html("Most recent exercises:");
            }
            self.showResults([{
                readable_id: "_",
                name: "_",
                title: "Loading...",
                display_name: "Loading..."
            }]);

            var url;
            if (this.type == "video") {
                url = "/api/v1/videos/recent";
            } else {
                url = "/api/v1/exercises/recent";
            }
            $.ajax({
                url: url,

                success: function(json) {
                    self.loaded = true;
                    self.showResults(json);
                }
            });
        },

        doSearch: function() {
            var searchText = $(this.el).find("input[name=\"item-search\"]").val();
            var self = this;

            if (this.type == "video") {
                $(this.el).find(".search-description").html("Videos matching \"" + searchText + "\":");
            } else {
                $(this.el).find(".search-description").html("Exercises matching \"" + searchText + "\":");
            }
            self.showResults([{
                readable_id: "",
                name: "",
                title: "Loading...",
                display_name: "Loading..."
            }]);

            $.ajax({
                url: "/api/v1/autocomplete?q=" + encodeURIComponent(searchText),

                success: function(json) {
                    self.loaded = true;
                    if (self.type == "video") {
                        self.showResults(json.videos);
                    } else {
                        self.showResults(json.exercises);
                    }
                }
            });
        },

        selectItem: function() {
            var itemID = $( this.el ).find("select.search-results option:selected").val();
            if ( !itemID ||
                itemID === "_") {
                return;
            }

            this.hide();

            var kind;
            if (this.type == "video") {
                kind = "Video";
            } else {
                kind = "Exercise";
            }

            this.callback(kind, itemID, this.results[itemID], null, null, -1);
        },

        hide: function() {
            return $( this.el ).modal("hide");
        }
    }),

    // Add a new exercise dialog box

    CreateExerciseView: Backbone.View.extend({
        template: Templates.get( "topicsadmin.create-exercise" ),

        initialize: function() {
            this.render();
        },

        events: {
            "click .ok-button": "createExercise"
        },

        render: function() {
            this.el = $( this.template( {type: this.type} ) ).appendTo(document.body).get(0);
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
            var name = $(this.el).find("input[name=\"name\"]").val();
            var exercise = new Exercise({ name: name });
            if ($(this.el).find("input[name=\"summative\"]").is(":checked")) {
                exercise.set({ summative: true });
            }

            exercise.save({}, {
                success: function() {
                    TopicTreeEditor.TopicEditor.finishAddExistingItem("Exercise", name, exercise.get("display_name"), null, null, -1);
                }
            });
            this.hide();
        },

        hide: function() {
            return $(this.el).modal("hide");
        }
    }),

    // Add a new video dialog box

    CreateVideoView: Backbone.View.extend({
        template: Templates.get( "topicsadmin.create-video" ),
        previewTemplate: Templates.get( "topicsadmin.create-video-preview" ),

        youtubeID: null,

        initialize: function() {
            this.render();
        },

        events: {
            "click .ok-button": "createVideo",
            "change input[name=\"youtube_id\"]": "doVideoSearch"
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
            $(this.el).find("input[name=\"youtube_id\"]").val("");
            $(this.el).find(".create-video-preview").html("Enter a YouTube ID to look up a video.");
            $(self.el).find(".ok-button").addClass("disabled").removeClass("green");
        },

        createVideo: function() {
            if (!this.youtubeID) {
                return;
            }

            var video = new Video({ youtube_id: this.youtubeID });

            video.save({}, {
                success: function(model) {
                    TopicTreeEditor.TopicEditor.finishAddExistingItem("Video", model.get("readable_id"), model.get("title"), null, null, -1);
                }
            });
            this.hide();
        },

        doVideoSearch: function() {
            var youtubeID = $(this.el).find("input[name=\"youtube_id\"]").val();
            var self = this;
            $.ajax({
                url: "/api/v1/videos/" + youtubeID + "/youtubeinfo",
                success: function(json) {
                    self.youtubeID = youtubeID;
                    $(self.el).find(".create-video-preview").html(self.previewTemplate(json));
                    $(self.el).find(".ok-button").removeClass("disabled").addClass("green");
                },
                error: function(json) {
                    self.youtubeID = null;
                    $(self.el).find(".create-video-preview").html("Video not found.");
                    $(self.el).find(".ok-button").addClass("disabled").removeClass("green");
                }
            });
        },

        hide: function() {
            return $(this.el).modal("hide");
        }
    }),

    // Add a new url dialog box

    CreateUrlView: Backbone.View.extend({
        template: Templates.get( "topicsadmin.create-url" ),

        initialize: function() {
            this.render();
        },

        events: {
            "click .ok-button": "createUrl"
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

            $(this.el).find("input[name=\"url\"]").val("");
        },

        createUrl: function() {
            var url = $(this.el).find("input[name=\"url\"]").val();
            var title = $(this.el).find("input[name=\"title\"]").val();
            var urlObject = new ExternalURL({ url: url, title: title });

            urlObject.save({}, {
                success: function(model) {
                    TopicTreeEditor.TopicEditor.finishAddExistingItem("Url", model.id, model.get("title"), null, null, -1);
                }
            });
            this.hide();
        },

        hide: function() {
            return $(this.el).modal("hide");
        }
    }),

    // View versions list

    VersionListView: Backbone.View.extend({
        template: Templates.get( "topicsadmin.list-versions" ),
        templateItem: Templates.get( "topicsadmin.list-versions-item" ),

        initialize: function() {
            this.render();
        },

        render: function() {
            this.el = $(this.template({})).appendTo(document.body).get(0);
            this.delegateEvents();
            return this;
        },

        show: function( type ) {
            $( this.el ).modal({
                keyboard: true,
                backdrop: true,
                show: true
            });

            var self = this;
            getTopicVersionList().fetch({
                success: function() {
                    var elements = [];
                    _.each( getTopicVersionList().models, function( model ) {
                        elements.push(
                            $( self.templateItem( model.toJSON() ) )
                                .find( "a.edit-version" )
                                    .click( function() { TopicTreeEditor.editVersion( model.get( "number" ) ); } )
                                    .end()
                        );
                    });
                    _.each( elements, function( element ) { element.appendTo( $( ".version-list", self.el ).get( 0 ) ); } );
                }
            });
            return this;
        },

        hide: function() {
            return $(this.el).modal("hide");
        }
    }),

    // Search popup

    SearchView: Backbone.View.extend({
        template: Templates.get( "topicsadmin.search-topics" ),
        visible: false,
        matchingPaths: null,
        currentIndex: 0,

        events: {
            "click .search-button": "toggle",
            "change input": "doSearch",
            "click .prev-button": "goToPrev",
            "click .next-button": "goToNext"
        },

        initialize: function() {
            this.render();
        },

        render: function() {
            this.el = $(this.template({})).get(0);
            this.delegateEvents();
            return this;
        },

        toggle: function() {
            this.visible = !this.visible;
            if (this.visible) {
                this.show();
            } else {
                this.hide();
            }
        },

        show: function() {
            $(".search-button", this.el).attr("src", "/images/circled_cross.png");
            $(".search-panel", this.el).slideDown(100);
        },

        hide: function() {
            $(".search-button", this.el).attr("src", "/images/jquery-mobile/icon-search-black.png");
            $(".search-panel", this.el).slideUp(100);
        },

        doSearch: function() {
            this.clearResults();

            el = $("input", this.el);
            query = el.val();
            if (query !== "") {
                var self = this;
                Throbber.show(el);
                $.ajax({
                    url: "/api/v1/topicversion/" + TopicTreeEditor.currentVersion.get("number") + "/search/" + query,
                    success: function(json) {
                        Throbber.hide();

                        var nodes = { };
                        _.each(json.nodes, function(node) {
                            nodes[node.kind] = nodes[node.kind] || [];
                            nodes[node.kind].push(node);
                        });
                        TopicTreeEditor.currentVersion.getTopicTree().addInited(nodes.Topic);
                        getExerciseList().addInited(nodes.Exercise);
                        getVideoList().addInited(nodes.Video);
                        getUrlList().addInited(nodes.URL);

                        self.matchingPaths = json.paths;
                        if (self.matchingPaths.length > 0) {
                            self.currentIndex = 0;
                            self.goToResult(0);
                        }
                    }
                });
            }
        },

        clearResults: function() {
            this.matchingPaths = [];
            $(".prev-button", this.el).attr("src", "/images/vote-up-gray.png");
            $(".next-button", this.el).attr("src", "/images/vote-down-gray.png");
        },

        goToResult: function(index) {
            var path = this.matchingPaths[index];
            var node = TopicTreeEditor.tree.getNodeByKey("Topic/root");
            var last_key = path[path.length-1] + "/" + path[path.length-2];

            _.each(path, function(key) {
                if (node) {
                    var nextNode = null;

                    node.expand(true);

                    KAConsole.log("Opening " + key + "...");

                    _.each(node.childList, function(childNode) {
                        if (childNode.data.key == last_key) {
                            childNode.activate();
                        } else if (childNode.data.key == ("Topic/"+key)) {
                            childNode.expand(true);
                            nextNode = childNode;
                        } else {
                            childNode.expand(false);
                        }
                    });

                    node = nextNode;
                }
            });

            this.currentIndex = index;
            $(".prev-button", this.el).attr("src", (this.currentIndex === 0) ? "/images/vote-up-gray.png" : "/images/vote-up.png");
            $(".next-button", this.el).attr("src", (this.currentIndex < this.matchingPaths.length - 1) ? "/images/vote-down.png" : "/images/vote-down-gray.png");
        },

        goToPrev: function() {
            if (this.currentIndex > 0) {
                this.goToResult(this.currentIndex - 1);
            }
        },
        goToNext: function() {
            if (this.currentIndex < this.matchingPaths.length - 1) {
                this.goToResult(this.currentIndex + 1);
            }
        }
    })
};
