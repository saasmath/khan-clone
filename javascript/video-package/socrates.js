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

// extract model from this?
Socrates.Question = Backbone.View.extend({
	className: "question",

	initialize: function() {
		_.extend(this, this.options);
		this.version = 1;
		this.loaded = false;
		this.render();
	},

	render: function() {
		// preload the image
		var img = document.createElement('img');
		img.src = this.imageUrl();
		this.$screenShotLayer = $("<div>", {"class": "layer screenshot"}).append(img);

		// preload html
		this.$controlsLayer = $("<div>", {"class": "layer controls"});
		$.get(this.htmlUrl()).success(_.bind(function(html) {
			this.$controlsLayer.html(html);
			this.loaded = true;
		}, this));

		// append to view. Still not added to DOM
		$(this.el)
			.append(this.$screenShotLayer)
			.append(this.$controlsLayer);

		return this;
	},

	submit: function() {
		var data = this.getData();
		return {
			timestamp: this.timestamp,
			youtubeId: this.youtubeId,
			id: this.id,
			version: this.version,
			correct: this.isCorrect(data),
			data: data
		};
	},

	key: function() {
		return this.youtubeId + "-" + this.timestamp;
	},

	htmlUrl: function() {
		return "/socrates/questions/" + this.key() + ".html";
	},

	imageUrl: function() {
		return "/socrates/questions/" + this.key() + ".jpeg";
	},

	isCorrect: function(data) {
		// todo: look at how khan-exercise does their fancy number handling
		return _.isEqual(data, this.correctData);
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
Socrates.Question.prototype.skip = Socrates.Question.prototype.submit;

// need to clean this up, I think it's a mixture of a Backbone.{View,Router}
Socrates.Controller = Backbone.View.extend({
	events: {
		'click .submit-area a.submit': 'submit',
		'click .submit-area a.skip': 'skip'
	},

	initialize: function() {
		this.videoControls = this.options.videoControls;
	},

	loadQuestions: function(questions) {
		this.$(".questions").append(_.pluck(questions, 'el'));

		var poppler = new Poppler();
		_.each(questions, function(question) {
			// subscribe to display event
			poppler.add(question.time, _.bind(this.show, this, question));
		}, this);

		// watch video time every 100 ms
		recursiveTrigger(_.bind(poppler.trigger, poppler));
	},

	show: function(question) {
		this.videoControls.pause();
		this.question = question;
		$(this.el).show();
		$(question.el).show();
	},

	submit: function() {
		var response = this.question.submit();
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
			'timestamp'];
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
		var response = this.question.skip();
		this.validateResponse(response);
		this.log('skip', response);

		$(this.el).hide();
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

$(function() {
	window.Controller = new Socrates.Controller({
		el: $(".video-overlay"),
		videoControls: window.VideoControls
	});

	nav = new Socrates.Nav({ el: ".socrates-nav" });
	nav.render();

	Controller.loadQuestions([
		new Socrates.Question({
			youtubeId: "xyAuNHPsq-g",
			timestamp: "000320.000",
			time: 4,
			id: "matrix-indexing-pre",
			correctData: { answer: "50" }
		}),
		new Socrates.Question({
			youtubeId: "xyAuNHPsq-g",
			timestamp: "000320.000",
			time: 3*60 + 20,
			id: "matrix-indexing",
			correctData: { answer: "2" }
		}),
		new Socrates.Question({
			youtubeId: "xyAuNHPsq-g",
			timestamp: "000441.000",
			time: 4*60 + 41,
			id: "matrix-uses",
			correctData: { answer: [true, true, true, true, true] }
		})
	]);
});

Socrates.Nav = Backbone.View.extend({
	template: Templates.get("video.socrates-nav"),

	render: function() {
		$(this.el).html(this.template());
		return this;
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
