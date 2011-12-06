var TopicTreeEditor = {
    tree: null,

    init: function() {
        var root = TopicTree.getRoot();
        root.bind("change", this.refreshTreeNode, root);

        // Attach the dynatree widget to an existing <div id="tree"> element
        // and pass the tree options as an argument to the dynatree() function:
        $("#topic_tree").dynatree({
            imagePath: '/images/',

            onActivate: function(node) {
                KAConsole.log('Activated: ', node);

                js = node.data.model.toJSON();
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
                        node.data.model.set(setter);
                        node.data.model.save();
                    }
                });
            },

            onLazyRead: function(node) {
                children = node.data.model.getChildren();
                children.bind("reset", TopicTreeEditor.refreshTreeChildren, node);
            },

            dnd: {
                onDragStart: function(node) {
                    return true;
                },

                onDragEnter: function(node, sourceNode) {
                    if (node.data.model.get('kind') != 'Topic')
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
                    isFolder: true,
                    isLazy: true,
                    model: root
            } ]
        });
        TopicTreeEditor.tree = $("#topic_tree").dynatree("getTree");
        $('#topic_tree').bind("mousedown", function(e) { e.preventDefault(); })
    },

    // Called with model as "this"
    refreshTreeNode: function() {
        KAConsole.log('refreshing ' + this.id);
        node = TopicTreeEditor.tree.getNodeByKey(this.id);
        node.setTitle(this.get("title"));
    },

    // Called with node as "this"
    refreshTreeChildren: function() {
        var node = this;
        KAConsole.log('refreshing children ' + node.data.model.get("readable_id"));
        node.removeChildren();
        if (node.data.model.children) {
            node.data.model.children.each(function(child) {
                var data = {
                    title: child.get("title"),
                    key:  child.id,
                    model: child
                };
                if (child.get('kind') == 'Topic') {
                    data.isFolder = true;
                    data.isLazy = true;
                } else if (child.get('kind') == 'Video') {
                    data.icon = 'video-camera-icon-full-small.png';
                } else if (child.get('kind') == 'Exercise') {
                    data.icon = 'exercise-icon-small.png';
                }
                node.addChild(data);
                child.bind("change", TopicTreeEditor.refreshTreeNode, child);
            });
        }
    }
};
