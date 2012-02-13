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

Socrates.Question = Backbone.Model.extend({
	seconds: function() {
		return Socrates.Question.timeToSeconds(this.get("time"));
	},

	key: function() {
		return this.get('youtubeId') + "-" + this.get('time');
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

Socrates.QuestionCollection = Backbone.Collection.extend({
	model: Socrates.Question
});

Socrates.QuestionView = Backbone.View.extend({
	className: "question",

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

	submit: function() {
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

	htmlUrl: function() {
		return "/socrates/questions/" + this.model.get('slug') + ".html";
	},

	imageUrl: function() {
		return "/socrates/questions/" + this.model.key() + ".jpeg";
	},

	isCorrect: function(data) {
		// todo: look at how khan-exercise does their fancy number handling
		return _.isEqual(data, this.model.get('correctData'));
	},

	getData: function() {
		// possible ideal impl: ask editing controls for info?

		// for now: do it myself.
		data = {};
		_.each(this.$controlsLayer.find("input"), function(el) {
			var $el = $(el);
			data[$el.attr("name")] = $(el).val();
		});
		return data;
	}
});

// alias skip to submit
Socrates.QuestionView.prototype.skip = Socrates.QuestionView.prototype.submit;

// need to clean this up, I think it's a mixture of a Backbone.{View,Router}
Socrates.SubmitView = Backbone.View.extend({
	events: {
		'click .submit-area a.submit': 'submit',
		'click .submit-area a.skip': 'skip'
	},

	initialize: function() {
		this.videoControls = this.options.videoControls;

		// wrap each model in a view
		this.views = this.model.map(function(question) {
			return new Socrates.QuestionView({model: question});
		});
	},

	render: function() {
		this.$(".questions").append(_.pluck(this.views, 'el'));
	},

	show: function(view) {
		if (view.__proto__ == Socrates.Question.prototype) {
			// recieved a question, find the corresponding view
			view = _.find(this.views, function(v) { return v.model == view; });
		}
		this.videoControls.pause();

		if (this.currentView) {
			this.currentView.hide();
		}
		this.currentView = view;

		$(this.el).show();
		this.currentView.show();
		return this;
	},

	hide: function() {
		if (this.currentView) {
			$(this.currentView.el).hide();
			this.currentView = null;
		}
		$(this.el).hide();
		return this;
	},

	submit: function() {
		var response = this.currentView.submit();
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

	skip: function() {
		var response = this.currentView.skip();
		this.validateResponse(response);
		this.log('skip', response);
		console.log(this.currentView);

		// clear the fragment
		Router.navigate("", false);

		console.log(this.currentView);
		window.VideoControls.player.seekTo(this.currentView.model.seconds());
		this.hide();
		window.VideoControls.play();
	},

	log: function(kind, response) {
		console.log("POSTing response", kind, response);
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
		":slug": "show"
	},

	initialize: function(options) {
		this.questions = options.questions;
		this.masterView = options.masterView;
		this.videoControls = options.videoControls;
	},

	show: function(slug) {
		// blank fragment for current state of video
		if (slug === "") {
			this.masterView.hide();
		}

		// slug for navigating to a particular question
		var question = this.questions.find(function(q) {
			return q.get('slug') == slug;
		});
		if (question) {
			this.masterView.show(question);
			return;
		}

		// todo: parse as a time, and seek to that time in the video
		if (/\d+m\d+s/.test(slug)) {
			var seconds = Socrates.Question.timeToSeconds(slug);
			this.videoControls.onPlayerReady(_.bind(function() {
				this.videoControls.player.seekTo(seconds);
			}, this));
			return;
		}

		// invalid fragment, replace it with nothing
		this.navigate("", {replace: true, trigger: true});
	},

	navigateToQuestion: function(question) {
		this.navigate(question.get('slug'));
		this.masterView.show(question);
	}
});

var Poppler = (function() {
	function Poppler() {
		this.events = [];
		this.duration = 0;
		_.bindAll(this);
	}

	Poppler.timeFn = function(e) { return e.time; };

	Poppler.nextPeriod = function(n, period) {
		return Math.round(Math.floor(n/period + 1)) * period;
	};

	Poppler.prototype.add = function(time, fn) {
		fn.time = time;
		var i = _.sortedIndex(this.events, Poppler.timeFn);
		this.events.splice(i, 0, fn);
	};

	Poppler.prototype.trigger = function trigger(time) {
		var epsilon = 0.001;
		// ignore duplicate triggers
		if (time == this.duration) return;

		if (time < this.duration) {
			// out of order, just treat as a seek
			this.seek(time);
			return;
		}

		// find the index for which all events prior to duration are to the left
		var i = _.sortedIndex(this.events, {time: this.duration}, Poppler.timeFn);

		// skip any events with times equal to the prior duration, as they were
		// executed in the last call
		while (this.events[i] && Math.abs(this.events[i].time - this.duration) < epsilon) {
			i++;
		}

		// get a new duration
		this.seek(time);

		// trigger events
		for (var j = i; this.events[j] && this.events[j].time <= this.duration; j++) {
			this.events[j]();
		}
	};

	Poppler.prototype.seek = function(time) {
		this.duration = time;
	};

	return Poppler;
})();

$(function() {
	window.Questions = new Socrates.QuestionCollection([
		new Socrates.Question({
			youtubeId: "xyAuNHPsq-g",
			time: "3m20s",
			id: 1,
			title: "Elements in a matrix",
			slug: "elements-in-a-matrix",
			correctData: { answer: "2" }
		}),
		new Socrates.Question({
			youtubeId: "xyAuNHPsq-g",
			time: "4m41s",
			id: 2,
			title: "What are matrices used for?",
			slug: "what-are-matrices-used-for",
			correctData: { answer: [true, true, true, true, true] }
		})
	]);

	window.SubmitView = new Socrates.SubmitView({
		el: $(".video-overlay"),
		videoControls: window.VideoControls,
		model: Questions
	});
	SubmitView.render();

	nav = new Socrates.Nav({
		el: ".socrates-nav",
		model: Questions
	});
	nav.render();

	window.Router = new Socrates.QuestionRouter({
		masterView: window.SubmitView,
		questions: window.Questions,
		videoControls: window.VideoControls
	});

	window.poppler = new Poppler();
	window.Questions.each(function(q) {
		poppler.add(q.seconds(), _.bind(Router.navigateToQuestion, Router, q));
	});

	// watch video time every 100 ms
	recursiveTrigger(_.bind(poppler.trigger, poppler));

	Backbone.history.start({
		root: "video/introduction-to-matrices?topic=linear-algebra-1#elements-in-a-matrix"
	});
});
