Socrates = {};

// this should work with a QuestionView
Socrates.ControlPanel = Backbone.View.extend({
	el: ".interactive-video-controls",

	controls: [],

	events: {
		'click button#label': 'addLabel',
		'click button#inputtext': 'addInputText'
	},

	addLabel: function() {
		this.addView(new Socrates.Label());
	},

	addInputText: function() {
		this.addView(new Socrates.InputText());
	},

	addView: function(view) {
		this.controls.push(view);

		// place in document before rendering, as jquery.ui checks if element is
		// positioned, and positioning is done in external CSS.
		this.$controlEl.append(view.el);
		view.render();
	},

	serializeHtml: function() {
		_.each(this.controls, function(c) {
			c.moveable(false);
		});
		return this.$controlEl.html();
	}
}, {
	onReady: function() {
		window.ControlPanel = new Socrates.ControlPanel();
	}
});

// Editing actions needed:
// 1. Lock / unlock moving (console)
// 2. Delete (console)
// 3. Edit text (dblclick)

Socrates.Label = Backbone.View.extend({
	tagName: "div",
	className: "label",

	events: {
		'dblclick': 'promptForContents'
	},

	render: function() {
		$(this.el).text('Default label contents');
		this.moveable(true);
		return this;
	},

	isMoveable: false,
	moveable: function(val) {
		if (val === this.isMoveable) return this;
		if (val == null) {
			val = !this.isMoveable;
		}
		this.isMoveable = val;

		if (this.isMoveable) {
			$(this.el)
				.addClass('moveable')
				.resizable()
				.draggable();
		} else {
			$(this.el)
				.removeClass('moveable')
				.resizable('destroy')
				.draggable('destroy');
		}

		return this;
	},

	promptForContents: function(evt) {
		var contents = prompt("Enter label contents", $(this.el).text());
		$(this.el).text(contents);
		if (this.isMoveable) {
			// need to toggle as .text() destroys the corner thing
			this.moveable(false);
			this.moveable(true);
		}
	},

	serializedForm: function() {

	}
});

Socrates.InputText = Backbone.View.extend({
	className: "inputtext",
	template: Templates.get("video.inputtext"),

	events: {
		'dblclick': 'promptForContents'
	},

	render: function() {
		var contents = this.template({
			placeholder: '?'
		});
		$(this.el).html(contents);
		this.moveable(true);
		return this;
	},

	isMoveable: false,
	moveable: function(val) {
		if (val === this.isMoveable) return this;
		if (val == null) {
			val = !this.isMoveable;
		}
		this.isMoveable = val;

		if (this.isMoveable) {
			$(this.el)
				.addClass('moveable')
				.resizable()
				.draggable();
		} else {
			$(this.el)
				.removeClass('moveable')
				.resizable('destroy')
				.draggable('destroy');
		}

		return this;
	},

	promptForContents: function(evt) {
		var $input = this.$('input');
		var contents = prompt("Enter placeholder contents",
			$input.attr('placeholder'));
		$input.attr('placeholder', contents);
	},

	serializedForm: function() {
		this.$('input').prop("disabled", false);
	}
});

$(Socrates.ControlPanel.onReady);

Socrates.Bookmark = Backbone.Model.extend({
	seconds: function() {
		return Socrates.Question.timeToSeconds(this.get("time"));
	},

	slug: function() {
		return _.str.slugify(this.get('title'));
	},

	toJSON: function() {
		var json = Backbone.Model.prototype.toJSON.call(this);
		json.slug = this.slug();
		return json;
	}
}, {
	timeToSeconds: function(time) {
		// convert a string like "4m21s" into just the number of seconds
		result = 0;
		var i = 0;
		while(time[i]) {
			var start = i;
			while(time[i] && /[\d\.,]/.test(time[i])) i++;
			var n = parseFloat(time.slice(start, i));
			var unit = time[i] || "s"; // assume seconds if reached end
			if (unit == "m") {
				result += n * 60;
			} else if (unit == "s") {
				result += n;
			} else {
				throw "Unimplemented unit, only ISO8601 durations with mins and secs";
			}
			i++;
		}
		return result;
	}
});

Socrates.Question = Socrates.Bookmark.extend({
	key: function() {
		return this.get('youtubeId') + "-" + this.get('time');
	}
});

Socrates.QuestionCollection = Backbone.Collection.extend({
	model: Socrates.Question
});

Socrates.QuestionView = Backbone.View.extend({
	className: "question",

	events: {
		'click .submit-area a.submit': 'submit',
		'click .submit-area a.skip': 'skip'
	},

	initialize: function() {
		_.extend(this, this.options);
		this.version = 1;
		this.loaded = false;
		this.render();
	},

	render: function() {
		// preload html
		$.get(this.htmlUrl()).success(_.bind(function(html) {
			$(this.el).html(html);
			this.loaded = true;
		}, this));

		return this;
	},

	hide: function() {
		$(this.el).hide();
		return this;
	},

	show: function() {
		$(this.el).show();
		return this;
	},

	htmlUrl: function() {
		return "/socrates/questions/" + this.model.slug() + ".html";
	},

	imageUrl: function() {
		return "/socrates/questions/" + this.model.key() + ".jpeg";
	},

	isCorrect: function(data) {
		var correctAnswer = this.model.get('correctData');

		// if no answer is specified, any answer is correct
		if (correctAnswer == null) {
			return true;
		}

		// otherwise make sure they got it right.
		// todo: look at how khan-exercise does their fancy number handling
		return _.isEqual(data, correctAnswer);
	},

	getData: function() {
		// possible ideal impl: ask editing controls for info?

		// for now: do it myself.
		data = {};

		// process all matrix-inputs
		var matrixInputs = this.$("table.matrix-input");
		_.each(matrixInputs, function(table) {
			var matrix = _.map($(table).find("tr"), function(tr) {
				return _.map($(tr).find("input"), function(input) {
					return parseFloat($(input).val());
				});
			});

			var name = $(table).attr("name") || "answer";
			data[name] = matrix;
		});

		// process all checkbox-grids
		var checkboxGrids = this.$("table.checkbox-grid");
		_.each(checkboxGrids, function(grid) {
			var headers = _.map($(grid).find("thead th"), function(td) {
				return $(td).attr("name");
			});
			headers = _.rest(headers, 1);
			var answer = {};
			_.each($(grid).find("tbody tr"), function(tr) {
				var row = {};
				_.each($(tr).find("input"), function(input, i) {
					row[headers[i]] = $(input).prop("checked");
				});
				answer[$(tr).attr("name")] = row;
			});

			var name = $(grid).attr("name") || "answer";
			data[name] = answer;
		});

		// process the result of the inputs
		var inputs = this.$("input").
			not(matrixInputs.find("input")).
			not(checkboxGrids.find("input"));

		_.each(inputs, function(el) {
			var $el = $(el);
			var key = $el.attr("name");

			var val;
			if (_.include(["checkbox", "radio"], $el.attr("type"))) {
				val = $el.prop("checked");
			} else {
				val = $el.val();
			}

			var isArray = false;
			if (data[key]) {
				if (!_.isArray(data[key])) {
					data[key] = [data[key]];
				}
				isArray = true;
			}

			if (isArray) {
				data[key].push(val);
			} else {
				data[key] = val;
			}
		});
		return data;
	},

	getResponse: function() {
		var data = this.getData();
		return {
			time: this.model.get('time'),
			youtubeId: this.model.get('youtubeId'),
			id: this.model.get('id'),
			version: this.version,
			correct: this.isCorrect(data),
			data: data
		};
	},

	validateResponse: function(response) {
		requiredProps = ['id', 'version', 'correct', 'data', 'youtubeId',
			'time'];
		var hasAllProps = _.all(requiredProps, function(prop) {
			return response[prop] != null;
		});
		if (!hasAllProps) {
			console.log(response);
			throw "Invalid response from question";
		}
		return true;
	},

	submit: function() {
		var response = this.getResponse();
		this.validateResponse(response);
		this.log('submit', response);

		if (response.correct) {
			console.log("correct");
			// todo: fancy correct animation
			// todo: skip explanation on correct
			$(this.el).hide();
			window.VideoControls.play();
		} else {
			console.log("incorrect!");
		}
	},

	skip: function() {
		var response = this.getResponse();
		this.validateResponse(response);
		this.log('skip', response);

		// clear the fragment
		Router.navigate("", false);

		window.VideoControls.player.seekTo(this.model.seconds(), true);
		this.hide();
		window.VideoControls.play();
	},

	log: function(kind, response) {
		console.log("POSTing response", kind, response);
	}
});

Socrates.MasterView = Backbone.View.extend({
	className: "video-overlay",

	initialize: function() {
		// wrap each question in a view
		this.views = this.model.
			filter(function(bookmark) {
				return bookmark.__proto__ == Socrates.Question;
			}).
			map(function(question) {
				return new Socrates.QuestionView({model: question});
			});
	},

	questionToView: function(view) {
		if (view.__proto__ == Socrates.Question.prototype) {
			// recieved a question, find the corresponding view
			view = _.find(this.views, function(v) { return v.model == view; });
		}
		return view;
	},

	render: function() {
		$(this.el).append(_.pluck(this.views, 'el'));
	}
});

var recursiveTrigger = function recursiveTrigger(triggerFn) {
	var t = VideoStats.getSecondsWatched();

	triggerFn(t);

	// schedule another call when the duration is probably ticking over to
	// the next tenth of a second
	t = VideoStats.getSecondsWatched();
	_.delay(recursiveTrigger, (Poppler.nextPeriod(t, 0.1) - t)*1000, triggerFn);
};

Socrates.Nav = Backbone.View.extend({
	template: Templates.get("video.socrates-nav"),

	render: function() {
		$(this.el).html(this.template({
			questions: this.model.toJSON()
		}));
		return this;
	}
});

Socrates.QuestionRouter = Backbone.Router.extend({
	routes: {
		":slug": "reactToNewFragment"
	},

	initialize: function(options) {
		this.questions = options.questions;
		this.masterView = options.masterView;
		this.videoControls = options.videoControls;
		this.beep = new Audio("/socrates/starcraft_chat_sound.mp3");
	},

	reactToNewFragment: function(slug) {
		// blank fragment for current state of video
		if (slug === "") {
			this.hide();
		}

		// slug for navigating to a particular question
		var question = this.questions.find(function(q) {
			return q.slug() == slug;
		});
		if (question) {
			this.enterState(question);
			return;
		}

		// todo: parse as a time, and seek to that time in the video
		if (slug.length > 0 && /(\d+m)?(\d+s)?/.test(slug)) {
			var seconds = Socrates.Question.timeToSeconds(slug);
			this.hide();
			this.videoControls.onPlayerReady(_.bind(function() {
				this.videoControls.player.seekTo(seconds);
			}, this));
			return;
		}

		// invalid fragment, replace it with nothing
		this.navigate("", {replace: true, trigger: true});
	},

	navigateToState: function(question, options) {
		this.navigate(question.slug());
		this.enterState(question, options);
	},

	enterState: function(view, options) {
		options = _.extend({}, options);

		this.leaveCurrentState();
		// this.videoControls.pause();

		if (options.beep) {
			this.beep.play();
		}

		nextView = this.masterView.questionToView(view);
		if (nextView) {
			this.currentView = nextView;
			if (this.currentView.show) {
				this.currentView.show();
			}
		}

		return this;
	},

	leaveCurrentState: function() {
		if (this.currentView) {
			if (this.currentView.hide)
				this.currentView.hide();
			this.currentView = null;
		}
		return this;
	}
});

Socrates.Skippable = (function() {
	var Skippable = function(options) {
		_.extend(this, options);
	};

	Skippable.prototype.seconds = function() {
		return _.map(this.span, Socrates.Question.timeToSeconds);
	};

	Skippable.prototype.trigger = function() {
		var pos = this.seconds()[1];
		this.videoControls.player.seekTo(pos, true);
	};

	return Skippable;
})();

$(function() {
	// todo: move this somewhere else, it's data not code
	window.Questions = new Socrates.QuestionCollection([
		new Socrates.Bookmark({
			time: "0m0s",
			title: "What is a matrix?"
		}),
		new Socrates.Bookmark({
			time: "0m59s",
			title: "Dimensions of a matrix"
		}),
		//{
	// 	time: "2m5.7s",
	// 	title: "Dimensions of a matrix",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 1,
	// 	correctData: { rows: "4", cols: "5" }
	// },
		new Socrates.Bookmark({
			time: "2m6s",
			title: "Referencing elements in a matrix"
		}),
		//{
	// 	time: "3m20s",
	// 	title: "Referencing elements in a matrix",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 2,
	// 	correctData: { answer: "2" }
	// },
		new Socrates.Bookmark({
			time: "3m28s",
			title: "What are matrices used for?"
		}),
		//{
	// 	time: "4m23.9s",
	// 	title: "What are matrices used for?",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 3,
	// 	correctData: { answer: [true, true, true, true, true, true] }
	// },
		new Socrates.Bookmark({
			time: "4m42s",
			title: "Defining matrix addition"
		}),
		//{
	// 	time: "6m31s",
	// 	title: "Defining matrix addition",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 4
	// },
		new Socrates.Bookmark({
			time: "6m31s",
			title: "Matrix addition"
		}),
		new Socrates.Bookmark({
		time: "7m39s",
		title: "Commutativity of matrix addition"
		}),
		//{
	// 	time: "8m9s",
	// 	title: "Commutativity of matrix addition",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 5
	// }, {
	// 	time: "8m10.5s",
	// 	title: "Matrix addition",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 6,
	// 	correctData: { answer: [[80, 23], [13, 25]] }
	// },
		new Socrates.Bookmark({
			time: "8m10s",
			title: "Matrix subtraction"
		}),
		new Socrates.Bookmark({
			time: "9m44s",
			title: "Matrices that can be added"
		}),
		new Socrates.Bookmark({
			time: "11m50s",
			title: "Matrix terminology"
		})
	//{
	// 	time: "11m50s",
	// 	title: "Matrix terminology",
	// 	youtubeId: "xyAuNHPsq-g",
	// 	id: 7,
	// 	correctData: {
	// 		"scalar": {"scalar": true, "row-vector": false, "column-vector": false, "matrix": false},
	// 		"column-vector": {"scalar": false, "row-vector": false, "column-vector": true, "matrix": true},
	// 		"row-vector": {"scalar": false, "row-vector": true, "column-vector": false, "matrix": true},
	// 		"matrix": {"scalar": false, "row-vector": false, "column-vector": false, "matrix": true}

	]);

	window.masterView = new Socrates.MasterView({
		el: $(".video-overlay"),
		videoControls: window.VideoControls,
		model: Questions
	});
	masterView.render();

	window.nav = new Socrates.Nav({
		el: ".socrates-nav",
		model: Questions
	});
	nav.render();

	window.Router = new Socrates.QuestionRouter({
		masterView: window.masterView,
		questions: window.Questions,
		videoControls: window.VideoControls
	});

	window.poppler = new Poppler();
	window.Questions.each(function(q) {
		poppler.add(q.seconds(), _.bind(Router.navigateToState, Router, q, {beep: true}));
	});

	// window.skippable = [
	// 	{span: ["25.5s", "42s"]},
	// 	{span: ["1m40s", "2m2s"]}
	// ];
	// skippable = _.map(skippable, function(item) {
	// 	return new Socrates.Skippable(_.extend(item, {videoControls: window.VideoControls}));
	// });
	// _.each(skippable, function(item) {
	// 	poppler.add(item.seconds()[0], _.bind(item.trigger, item));
	// });

	// watch video time every 100 ms
	recursiveTrigger(_.bind(poppler.trigger, poppler));

	Backbone.history.start({
		root: "video/introduction-to-matrices?topic=linear-algebra-1#elements-in-a-matrix"
	});
});
