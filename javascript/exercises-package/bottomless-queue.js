/**
 * BottomlessQueue returns a never-ending sequence of
 * Exercise and UserExercise objects once primed with
 * some initial exercises.
 *
 * It'll talk to our API to try to find the best next
 * exercises in the queue when possible.
 *
 * BottomlessQueue is responsible for holding onto
 * and updating all userExercise objects, and it
 * passes them on to khan-exercises when khan-exercises
 * needs 'em.
 */
Exercises.BottomlessQueue = {

    // # of exercises we keep around as "recycled"
    // in case we need to re-use them if ajax requests
    // have failed to refill our queue.
    recycleQueueLength: 5,

    // # of exercises in queue below which we will
    // send off an ajax request for a refill
    queueRefillSize: 3,

    // # of exercises in upcoming queue for which we
    // trigger upcomingExercise events to give
    // listeners a chance to preload resources
    preloadUpcoming: 2,

    // true if there's a refill request currently pending
    refilling: false,

    initDeferred: $.Deferred(),

    sessionStorageEnabled: null,

    currentQueue: [],
    recycleQueue: [],

    // current item that was most recently popped off the queue
    current: null,

    // STOPSHIP TODO(kamens): userExerciseCache needs to be hidden via
    // closures to prevent simple cheating
    //
    // Nuke the global userExercise object to make
    // it significantly harder to cheat:

    /* try {
        delete window.userExercise;
    }
    catch(e) {} // swallow exception from IE
    finally {
        if (window.userExercise) {
            window.userExercise = undefined;
        }
    }
    */

    // Cache of userExercise objects for
    // each exercise we encounter
    userExerciseCache: {},

    init: function(userExercises) {

        this.sessionStorageEnabled = this.testSessionStorage();

        // Delay some initialization until after khan-exercises
        // is all set up
        this.initDeferred.done(function() {

            if (!Exercises.BottomlessQueue.sessionStorageEnabled) {
                Exercises.BottomlessQueue.warnSessionStorageDisabled();
            }

            // Fill up our queue and cache with initial exercises sent
            // on first pageload
            _.each(userExercises, function(userExercise) {
                this.enqueue(this.checkCacheForLatest(userExercise));
            }, Exercises.BottomlessQueue);

        });

        // Any time khan-exercises tells us it has new updateUserExercise
        // data, update cache if it's more recent
        $(Khan)
            .bind("updateUserExercise", function(ev, userExercise) {
                Exercises.BottomlessQueue.cacheLocally(userExercise);
            })
            .bind("attemptError", function(ev, userExercise) {
                Exercises.BottomlessQueue.clearCache(userExercise);
            })
            .bind("problemDone", function() {

                // Whenever a problem is completed, we may be waiting for
                // a while for the /attempt callback to finish and send us the
                // server's updated userExercise data. So we cheat a bit and
                // bump up the just-finished userExercises's totalDone count
                // here in case we run into it again before the ajax call
                // returns.
                var currentExercise = Exercises.BottomlessQueue.current.exercise,
                    userExercise = Exercises.BottomlessQueue.userExerciseCache[currentExercise];

                if (userExercise) {
                    userExercise.totalDone += 1;
                }

            });

    },

    testSessionStorage: function() {
        // Adapted from a comment on http://mathiasbynens.be/notes/localstorage-pattern
        var enabled, uid = +new Date;
        try {
            sessionStorage[ uid ] = uid;
            enabled = ( sessionStorage[ uid ] == uid );
            sessionStorage.removeItem( uid );
            return enabled;
        }
        catch( e ) {
            return false;
        }
    },

    warnSessionStorageDisabled: function() {
        $(Exercises).trigger("warning", ["You must enable DOM storage in your browser; see <a href='https://sites.google.com/a/khanacademy.org/forge/for-developers/how-to-enable-dom-storage'>here</a> for instructions.", false] );
    },

    enqueue: function(userExercise) {

        // Push onto current queue
        this.currentQueue.push({
            "exercise": userExercise.exercise,
            // true if we've triggered an upcomingExercise event for this queue entry
            "upcomingTriggered": false
        });

        // Cache userExercise
        this.cacheLocally(userExercise);

        // Possibly new upcoming exercises
        this.triggerUpcoming();

    },

    /**
     * Make sure an upcomingExercise event has been triggered for the 
     * first this.preloadUpcoming events in currentQueue.
     */
    triggerUpcoming: function() {

        _.each(this.currentQueue, function(item, ix) {

            if (!item.upcomingTriggered && ix < this.preloadUpcoming) {

                // Tell khan-exercises to preload this upcoming exercise if it hasn't
                // already
                $(Exercises).trigger("upcomingExercise", item.exercise);

                item.upcomingTriggered = true;

            }

        }, this);

    },

    cacheKey: function(userExercise) {
        return "userexercise:" + userExercise.user + ":" + userExercise.exercise;
    },

    /**
     * checkCacheForLatest returns the userExercise passed in
     * unless there is a locally cached version in sessionStorage
     * that looks to be more up-to-date than userExercise.
     * It's used to maintain nice back-button behavior
     * when navigating around exercises so you don't lose your place.
     */
    checkCacheForLatest: function(userExercise) {

        if (!userExercise) {
            return null;
        }

        // Parse the JSON if it exists
        var data = window.sessionStorage[this.cacheKey(userExercise)],
            oldUserExercise = data ? JSON.parse(data) : null;

        if (oldUserExercise && oldUserExercise.totalDone > userExercise.totalDone) {
            // sessionStorage-cached data is newer than userExercise. Probably
            // got here via browser history.
            return oldUserExercise;
        } else {
            return userExercise;
        }

    },

    cacheLocally: function(userExercise) {

        if (!userExercise) {
            return;
        }

        var oldUserExercise = this.userExerciseCache[userExercise.exercise];

        // Update cache, if new data is more recent
        if (!oldUserExercise || (userExercise.totalDone >= oldUserExercise.totalDone)) {

            this.userExerciseCache[userExercise.exercise] = userExercise;

            // Persist to session storage so we get nice back button behavior
            window.sessionStorage[this.cacheKey(userExercise)] = JSON.stringify(userExercise);
        }

    },

    clearCache: function(userExercise) {

        if (!userExercise) {
            return;
        }

        // Before we reload after an error, clear out sessionStorage.
        // If there' a discrepancy between server and sessionStorage such that
        // problem numbers are out of order or anything else, we want
        // to restart with whatever the server sends back on reload.
        delete this.userExerciseCache[userExercise.exercise];
        delete window.sessionStorage[this.cacheKey(userExercise)];

    },

    next: function() {

        if (!this.initDeferred.isResolved()) {
            this.initDeferred.resolve();
        }

        if (!this.sessionStorageEnabled) {
            return null;
        }
        
        // If the queue is empty, use the recycle queue
        // to fill up w/ old problems while we wait for
        // an ajax request for more exercises to complete.
        if (!this.currentQueue.length) {
            this.currentQueue = this.recycleQueue;
            this.recycleQueue = [];
        }

        // We don't ever expect to find an empty queue at
        // this point. If we do, we've got a problem.
        if (!this.currentQueue.length) {
            throw "No exercises are in the queue";
        }

        // Pull off the next exercise
        this.current = _.head(this.currentQueue);

        // If we don't have a userExercise object for the next
        // exercise, we've got a problem.
        if (!this.userExerciseCache[this.current.exercise]) {
            throw "Missing user exercise cache for next exercise";
        }

        // Remove it from current queue...
        this.currentQueue = _.rest(this.currentQueue);

        // ...but put it on the end of our recycle queue
        this.recycleQueue.push(this.current);

        // ...and then chop the recycle queue down so it
        // doesn't just constantly grow.
        this.recycleQueue = _.last(this.recycleQueue, Math.min(5, this.recycleQueue.length));

        // Refill if we're running low
        if (this.currentQueue.length < this.queueRefillSize) {
            this.refill();
        }

        // Possibly new upcoming exercises
        this.triggerUpcoming();

        return this.userExerciseCache[this.current.exercise];
 
    },

    refill: function() {

        if (this.refilling) {
            // Only one refill request at a time
            return;
        }

        this.refilling = true;

        $.ajax({
            // TODO(kamens): this URL needs a real topic id
            // TODO(kamens): this also probably needs a review URL toggle
            url: "/api/v1/user/topic/<topic_id>/exercises/next",
            type: "GET",
            dataType: "json",
            data: {
                queued: [], // TODO(kamens): list of queued needs work
                casing: "camel"
            },
            complete: function() {
                Exercises.BottomlessQueue.refilling = false;
            },
            success: function(data) {
                _.each(data, function(userExercise) {
                    Exercises.BottomlessQueue.enqueue(userExercise);
                });
            }
        });

    }

};
