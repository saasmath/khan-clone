// These models can automatically fetch the tree incrementally
// using API calls during traversal. Note that the getChildren()
// call is asynchronous.

function TestTopics() {
	KAConsole.debugEnabled = true;

    var tree = getDefaultTopicTree();
    var root = tree.getRoot();
    KAConsole.log('Fetching root...');
    root.fetch({
        success: function() {
            KAConsole.log('Got root. Fetching child...');
            var child = root.getChild('math');
            child.fetch({
                success: function() {
                    KAConsole.log('Got child topic', child);
                }
            });
        }
    });
}

(function() {
	var defaultTree = null;

	Topic = Backbone.Model.extend({
		defaults: {
            // Short version
			id: 'new_topic', // API ID / slug
			title: 'New Topic',
            standalone_title: 'New Topic',
			kind: 'Topic',

            // Long version
			description: '',
			hide: false,
			ka_url: '',
			tags: [],
			children: []
		},

		initialize: function() {
			this.url = '/api/v1/topic/' + this.get('id');
		},

        getChild: function(id) {
            var found = false;
            _.each(this.get('children'), function(child) {
                if (child.id == id) {
                    found = true;
                }
            });
            if (found)
                return this.tree.get(id);
            return null;
        },
        getChildren: function() {
            childModels = [];
            var self = this;
            _.each(this.get('children'), function(child) {
                childModels.push(self.tree.get(child.id));
            });
            return childModels;
        }
	});

	TopicTree = Backbone.Collection.extend({
		model: Topic,

        getRoot: function() {
            if (!this.get('root')) {
                var rootNode = new Topic({
					id: 'root',
					title: 'Loading...'
                });
                this.addNode(rootNode);
            }

            return this.get('root');
        },

        addNode: function(node) {
            KAConsole.log('Adding node to tree: ' + node.get('id'));
            node.tree = this;
            this.add([ node ]);
            node.bind('change', this.updateNode, node);
        },

        updateNode: function() {
            var node = this;
            var tree = node.tree;

            node.inited = true;

            _.each(node.get('children'), function(child) {
                if (child.kind == 'Topic' && !tree.get(child.id)) {
                    var newNode = new Topic(child);
                    tree.addNode(newNode);
                }
            });
        },
	});

    getDefaultTopicTree = function() {
        if (!defaultTree) {
            defaultTree = new TopicTree();
        }
        return defaultTree;
    }

    Video = Backbone.Model.extend({
        defaults: {
            readable_id: 'new_video', // API ID / slug
			kind: 'Video',
            title: 'New Video',
            youtube_id: '',
            description: '',
            keywords: '',
            duration: 0,
            views: 0,
            date_added: '',
            url: '',
            ka_url: '',
            relative_url: '',
            download_urls: null,
        },

        idAttribute: 'readable_id',

        urlRoot: '/api/v1/videos'
    });

    Exercise = Backbone.Model.extend({
        defaults: {
            name: 'new_exercise', // API ID / slug
			kind: 'Exercise',
            display_name: 'New Exercise', 
            short_display_name: 'New Ex', 
            creation_date: '', 
            h_position: 0, 
            v_position: 0,
            live: false, 
            summative: false, 
            num_milestones: 0, 
            seconds_per_fast_problem: 0, 
            covers: [], 
            prerequisites: [], 
            ka_url: '', 
            relative_url: ''
        },

        idAttribute: 'name',

        urlRoot: '/api/v1/exercises'
    });

})();
