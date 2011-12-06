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
                if (node.data.kind == 'Topic') {
                    var model = topicTree.get(node.data.key);
                    if (!model.inited) {
                        $('#details_view').html('Loading...');
                        model.fetch({
                            success: function() {
                                TopicDetailEditor.init(model);
                            }
                        });
                    } else {
                        TopicDetailEditor.init(model);
                    }
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
                    sourceNode.move(node, hitMode);
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

var TopicDetailEditor = {
    init: function(model) {
        js = model.toJSON();
        html = '<table>';
        for (field in js) {
            className = '';
            if (field == 'id')
                continue;
            if (field == 'title'|| field == 'description' || field == 'display_name' || field == 'name' || field == 'readable_id' || field == 'keywords')
                className = 'editable';
            html += '<tr><td><b>' + field + '</b></td><td><span data-id="' + field + '" class="' + className + '">' + js[field] + '</span></td></tr>';
        }
        html += '</table>';
        $('#details_view').html(html);
        $('#details_view').find('span.editable').editable({
            editBy: 'click',
            onEdit: function(content) {
                var field = this.attr('data-id');
                var setter = {};
                setter[field] = content.current;
                model.set(setter);
                model.save();
            }
        });
    }
};
