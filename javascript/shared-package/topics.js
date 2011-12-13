// These models can automatically fetch the tree incrementally
// using API calls during traversal. Note that the fetchById()
// call may be either synchronous or asynchronous, depending on
// whether the model is already in the cache.

function TestTopics() {
	KAConsole.debugEnabled = true;

    var tree = getDefaultTopicTree();
    KAConsole.log('Fetching root...');
    tree.fetchByID('root',
        function() {
            KAConsole.log('Got root. Fetching first child...');
            tree.fetchByID(this.get('children')[0].id,
                function() {
                    KAConsole.log('Got child topic:', this);
                }
            );
        }
    );
}

// TomY TODO - Move this to some shared Backbone utils file?
IncrementalCollection = Backbone.Collection.extend({
    fetchByID: function(id, callback, args) {
        var ret = this.get(id);
        if (!ret) {
            if (!this.idAttribute) {
                this.idAttribute = new this.model({}).idAttribute;
                if (!this.idAttribute)
                    this.idAttribute = 'id';
            }

            var attrs = {};
            attrs[this.idAttribute] = id;
            ret = this._add(attrs);
        }
        if (!ret.__inited) {
            if (!ret.__callbacks)
                ret.__callbacks = [];
            if (callback)
                ret.__callbacks.push({ callback: callback, args: args });

            if (!ret.__requesting) {
                KAConsole.log('IC (' + id + '): Sending request...');
                ret.fetch({
                    success: function() {
                        KAConsole.log('IC (' + id + '): Request succeeded.');
                        ret.__inited = true;
                        ret.__requesting = false;
                        _.each(ret.__callbacks, function(cb) {
                            cb.callback.apply(ret, cb.args);
                        });
                        ret.__callbacks = [];
                    },

                    error: function() {
                        KAConsole.log('IC (' + id + '): Request failed!');
                        ret.__requesting = false;
                    }
                });
                ret.__requesting = true;
            } else {
                KAConsole.log('IC (' + id + '): Already requested.');
            }
        } else {
            KAConsole.log('IC (' + id + '): Already loaded.');
            if (callback)
                callback.apply(ret, args);
        }

        return ret;
    },
    resetInited: function(models, options) {
        this.reset(models, options);
        _.each(this.models, function(model) {
            model.__inited = true;
        });
    },
});

// Model/collection for Topics
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
			this.url = '/api/v1/topicversion/edit/topic/' + this.get('id');
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
        },

        addChild: function(child, idx) {
            child_list = this.get('children').slice(0);
            child_list.splice(idx, 0, child);
            this.set({'children': child_list});
        },
        removeChild: function(kind, id) {
            var ret = null;
            var child_list = _.filter(this.get('children'), function(child) {
                if (child.kind != kind || child.id != id)
                    return true;
                ret = child;
                return false;
            });
            this.set({'children': child_list});
            return ret;
        },
	});

	TopicTree = IncrementalCollection.extend({
		model: Topic,

        getRoot: function() {
            ret = this.fetchByID('root');
            if (!ret.__inited)
                ret.set({title: 'Loading...'});
            return ret;
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

            // Insert "placeholder" nodes into tree so we can track changes
            _.each(node.get('children'), function(child) {
                if (child.kind == 'Topic' && !tree.get(child.id)) {
                    var newNode = new Topic(child);
                    tree.addNode(newNode);
                    child.__ptr = newNode;
                }
            });

            // Update child lists
            tree.each(function(other_node) {
                var children = _.map(other_node.get('children'), function(child) {
                    if (child.__ptr && child.__ptr.__inited) {
                        return {
                            kind: child.kind,
                            __ptr: child.__ptr,
                            id: child.__ptr.id,
                            title: child.__ptr.get('title'),
                            hide: child.__ptr.get('hide')
                        };
                    } else {
                        return child;
                    }
                });
                other_node.set({'children':children});
            });
        },
	});

    getDefaultTopicTree = function() {
        if (!defaultTree) {
            defaultTree = new TopicTree();
        }
        return defaultTree;
    };

})();

// Model/collection for Videos
(function() {

	var videoList = null;

    Video = Backbone.Model.extend({
        defaults: {
            readable_id: '', // API ID / slug
			kind: 'Video',
            title: '',
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

	VideoList = IncrementalCollection.extend({
		model: Video
    });

    getVideoList = function() {
        if (!videoList) {
            videoList = new VideoList();
        }
        return videoList;
    };

})();

// Model/collection for Exercises

(function() {

	var exerciseList = null;

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

	ExerciseList = IncrementalCollection.extend({
		model: Exercise
    });

    getExerciseList = function() {
        if (!exerciseList) {
            exerciseList = new ExerciseList();
        }
        return exerciseList;
    };

})();
