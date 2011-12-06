// These models can automatically fetch the tree incrementally
// using API calls during traversal. Note that the getChildren()
// call is asynchronous.

function TestTopics() {
	KAConsole.debugEnabled = true;

	var root = TopicTree.getRoot();
	root.getChildren({
		success: function(collection) {
			var biology = collection.get('biology');
			KAConsole.log('Got biology topic', biology);
		}
	});
}

(function() {
	var rootTopic = null;

	Topic = Backbone.Model.extend({
		defaults: {
			title: 'New Topic',
			description: '',
			kind: 'Topic',
			readable_id: '',
			hide: false,
			ka_url: '',
			tags: [],

			// Run-time fields
			children: null
		},

		initialize: function() {
			var id = '';
			var title = '';
			var kind = this.get('kind');
			if (kind == 'Topic' || kind == 'Video') {
				id = this.get('readable_id');
				title = this.get('title');
			}
			else if (kind == 'Exercise') {
				id = this.get('name');
				title = this.get('display_name');
			}
			this.set({id: id, title: title});
			this.url = '/api/v1/topic/' + id;

		},

		getChildren: function(options) {
			if (!this.children) {
				var newList = new TopicList();
				newList.url = this.url + '/children';
				newList.fetch(options);
				this.children = newList;
			}
			return this.children;
		},
	});

	TopicList = Backbone.Collection.extend({
		model: Topic
	});

	TopicTree = {
		getRoot: function() {
			if (!rootTopic) {
				rootTopic = new Topic({
					readable_id: 'root',
					title: 'Loading...'
				});
				rootTopic.fetch();
			}
			return rootTopic;
		}
	};
})();
