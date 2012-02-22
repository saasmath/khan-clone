// Poppler is an event triggering library for streams.

var Poppler = (function() {
    function Poppler() {
        this.events = [];
        this.duration = -1;
        this.eventIndex = 0;
        _.bindAll(this);
    }

    Poppler.timeFn = function(e) { return e.time; };

    Poppler.nextPeriod = function(n, period) {
        return Math.round(Math.floor(n / period + 1)) * period;
    };

    Poppler.prototype.add = function(time, fn) {
        fn.time = time;
        var i = _.sortedIndex(this.events, fn, Poppler.timeFn);

        // if there are existing elements with the same time, insert afterwards
        while (this.events[i] && this.events[i].time == time) i++;

        this.events.splice(i, 0, fn);
    };

    Poppler.prototype.trigger = function trigger(time) {
        if (this.blocked) return;

        var delta = time - this.duration;

        // ignore duplicate triggers
        var epsilon = 0.001;
        if (Math.abs(delta) < epsilon) return;

        // ignore any huge jumps
        var maxJumpSize = 1;
        if (Math.abs(delta) > maxJumpSize) return;

        // get a new duration
        this.duration = time;
        this.triggerEvents();
    };

    Poppler.prototype.triggerEvents = function() {
        while (this.events[this.eventIndex] && this.events[this.eventIndex].time <= this.duration) {
            var blocking = this.events[this.eventIndex]();
            this.eventIndex++;
            if (blocking) {
                this.blocked = true;
                break;
            }
        }
    };

    Poppler.prototype.resumeEvents = function() {
        this.blocked = false;
        this.triggerEvents();
    };

    Poppler.prototype.seek = function(time) {
        this.duration = time;
        this.eventIndex = _.sortedIndex(this.events, {time: this.duration}, Poppler.timeFn);
    };

    return Poppler;
})();
