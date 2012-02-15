// Poppler is an event triggering library for streams.

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
		var i = _.sortedIndex(this.events, fn, Poppler.timeFn);
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
