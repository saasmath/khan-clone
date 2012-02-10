Socrates = {};

Socrates.ControlPanel = Backbone.View.extend({
	el: ".interactive-video-controls",

	controls: [],

	events: {
		'click #toggle': 'toggle',
		'click button#label': 'addLabel',
		'click button#inputtext': 'addInputText'
	},

	initialize: function(options) {
		this.overlayEl = options.overlayEl;
		this.$overlayEl = $(this.overlayEl);

		this.$controlEl = this.$overlayEl.find('.layer.question');
	},

	toggle: function() {
		this.$overlayEl.toggle();
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
		window.ControlPanel = new Socrates.ControlPanel({
			overlayEl: $('.video-overlay')
		});
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

Socrates.Question = (function() {
	function Question(options) {
		this.version = 1;
		_.extend(this, options);
	}

	Question.prototype.submit = function() {
		var data = this.getData();
		return {
			timestamp: this.timestamp,
			youtubeId: this.youtubeId,
			id: this.id,
			version: this.version,
			correct: this.isCorrect(data),
			data: data
		};
	};

	// may as well alias skip to submit...
	Question.prototype.skip = Question.prototype.submit;

	Question.prototype.render = function() {
		$.get(this.htmlUrl()).success($.proxy(function(html) {
			this.$controlsArea.html(html);
			this.$frameImg.attr("src", this.imageUrl());
		}, this));
	};

	Question.prototype.key = function() {
		return this.youtubeId + "-" + this.timestamp;
	};

	Question.prototype.htmlUrl = function() {
		return "/socrates/questions/" + this.key() + ".html";
	};

	Question.prototype.imageUrl = function() {
		return "/socrates/questions/" + this.key() + ".jpeg";
	};

	Question.prototype.isCorrect = function(data) {
		// todo: look at how khan-exercise does their fancy number handling
		return _.isEqual(data, this.correctData);
	};

	Question.prototype.getData = function() {
		// possible ideal impl: ask editing controls for info?

		// for now: do it myself.
		data = {};
		_.each(this.$controlsArea.find("input"), function(el) {
			var $el = $(el);
			data[$el.attr("name")] = $(el).val();
		});
		return data;
	};
	return Question;
})();

// need to clean this up, I think it's a mixture of a Backbone.{View,Router}
Socrates.Controller = (function() {
	function Controller() {
		_.bindAll(this);

		$(".video-overlay .submit-area")
			.on("click", "a.submit", this.submit)
			.on("click", "a.skip", this.skip);

		// this does not beling here
		$("#trigger").on("click", this.triggerQuestion);
	}

	Controller.prototype.clear = function() {
		this.question = null;
		$(".video-overlay .layer.question").empty();
		$(".video-overlay .layer.screenshot .video-frame")
			.attr("src", "")
			.hide();
	};

	Controller.prototype.load = function(question) {
		this.question = question;

		question.$controlsArea = $(".video-overlay .layer.question");
		question.$frameImg = $(".video-overlay .layer.screenshot .video-frame");
		question.render();
		question.$frameImg.show();
	};

	Controller.prototype.validateResponse = function(response) {
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
	};

	Controller.prototype.submit = function() {
		var response = this.question.submit();
		this.validateResponse(response);

		this.log('submit', response);

		if (response.correct) {
			console.log("correct");
		} else {
			console.log("incorrect!");
		}

		this.resume();
	};

	Controller.prototype.skip = function() {
		var response = this.question.skip();
		this.validateResponse(response);

		this.log('skip', response);
		this.resume();
	};

	Controller.prototype.resume = function() {
		window.ControlPanel.$overlayEl.hide();
		// seek to correct spot?
		window.VideoControls.play();
	};

	Controller.prototype.triggerQuestion = function() {
		window.VideoControls.pause();
		ControlPanel.$overlayEl.show();
	};

	Controller.prototype.log = function(kind, response) {
		console.log("POSTing response", kind, response);
	};

	return Controller;
})();

$(function() {
	window.Controller = new Socrates.Controller();
	// display a question
	window.InlineQuestion = new Socrates.Question({
		youtubeId: "xyAuNHPsq-g",
		timestamp: "000320.000",
		id: "matrix-indexing",
		correctData: { answer: "2" }
	});
	window.Controller.load(InlineQuestion);
});
