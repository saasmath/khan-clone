/**
 * Model of any (current or in-stack) card
 */
Exercises.Card = Backbone.Model.extend({

    leaves: function(card) {

        return _.map(_.range(4), function(index) {
            
            return {
                index: index,
                state: (this.get("leavesEarned") > index ? "earned" : 
                            this.get("leavesAvailable") > index ? "available" :
                                "unavailable")
            };

        }, this);

    },

    /**
     * Decreases leaves available -- if leaves available is already at this
     * level or lower, noop
     */
    decreaseLeavesAvailable: function(leavesAvailable) {

        var currentLeaves = this.get("leavesAvailable");
        if (currentLeaves) {
            leavesAvailable = Math.min(currentLeaves, leavesAvailable);
        }

        return this.set({ leavesAvailable: leavesAvailable });

    },

    /**
     * Increases leaves earned for this card -- if leaves earned is already
     * at this level or higher, noop
     */
    increaseLeavesEarned: function(leavesEarned) {

        var currentLeaves = this.get("leavesEarned");
        if (currentLeaves) {
            leavesEarned = Math.max(currentLeaves, leavesEarned);
        }

        // leavesEarned takes precedence over leavesAvailable because
        // leavesEarned is only set when the card is done, and leavesAvailable
        // no longer matters at this point.
        // 
        // We update leavesAvailable here just to keep the card's data consistent.
        return this.set({ leavesEarned: leavesEarned, leavesAvailable: leavesEarned });

    },

});

/**
 * Collection model of a stack of cards
 */
Exercises.StackCollection = Backbone.Collection.extend({

    model: Exercises.Card,

    peek: function() {
        return _.head(this.models);
    },

    pop: function(animationOptions) {
        var head = this.peek();
        this.remove(head, animationOptions);
        return head;
    },

    /**
     * Shrink this stack by removing N cards up to but not including
     * the first card in the stack and the last (end of stack) card.
     */
    shrinkBy: function(n) {

        // Never shrink to less than two cards (first card, end of stack card).
        var targetLength = Math.max(2, this.length - n);

        while (this.length > targetLength) {
            // Remove the second-to-last card until we're done.
            this.remove(this.models[this.length - 2]);
        }

    },

    /**
     * Return the longest streak of cards in this stack
     * that satisfies the truth test fxn
     */
    longestStreak: function(fxn) {

        var current = 0,
            longest = 0;

        this.each(function(card) {

            if (fxn(card)) {
                current += 1;
            } else {
                current = 0;
            }

            longest = Math.max(current, longest);

        });

        return longest;

    },

    /**
     * Return a dictionary of interesting, positive stats about this stack.
     */
    stats: function() {

        var totalLeaves = this.reduce(function(sum, card) {
            return card.get("leavesEarned") + sum;
        }, 0);

        var longestStreak = this.longestStreak(function(card) {
            return card.get("leavesEarned") >= 3;
        });

        var longestSpeedStreak = this.longestStreak(function(card) {
            return card.get("leavesEarned") >= 4;
        });

        return {
            "longestStreak": longestStreak,
            "longestSpeedStreak": longestSpeedStreak,
            "totalLeaves": totalLeaves
        };
    }

});

/**
 * StackCollection that is automatically cached in localStorage when modified
 * and loads itself from cache on initialization.
 */
Exercises.CachedStackCollection = Exercises.StackCollection.extend({

    userTopic: null,

    initialize: function(models, options) {

        this.userTopic = options.userTopic;

        // Try to load models from cache
        if (!models) {
            this.loadFromCache();
        }

        this
            .bind("add", this.cache, this)
            .bind("remove", this.cache, this);

        return Exercises.StackCollection.prototype.initialize.call(this, models, options);

    },

    cacheKey: function() {
        return [
            "cachedstack",
            this.userTopic.get("user"),
            this.userTopic.get("name")
        ].join(":");
    },

    loadFromCache: function() {
        var data = window.localStorage[this.cacheKey()];

        if (data) {
            _.each(JSON.parse(data), function(dict) {
                this.add(new Exercises.Card(dict), {at: 0})
            }, this);
        }
    },

    cache: function() {

        try {
            window.localStorage[this.cacheKey()] = JSON.stringify(this.models);
        } catch(e) {
            // If we had trouble storing in localStorage, we may've run over
            // the browser's 5MB limit. This should be rare, but when hit, clear
            // everything out.
            this.clearAllCache();
        }
    },

    /**
     * Delete this stack from localStorage
     */
    clearCache: function() {
        delete window.localStorage[this.cacheKey()];
    },

    /**
     * Delete all cached stack objects from localStorage
     */
    clearAllCache: function() {
        var i = 0;
        while (i < localStorage.length) {
            var key = localStorage.key(i);
            if (key.indexOf('cachedstack:') === 0) {
                delete localStorage[key];
            }
            else {
                i++;
            }
        }
    }

});

/**
 * View of a stack of cards
 */
Exercises.StackView = Backbone.View.extend({

    template: Templates.get("exercises.stack"),

    initialize: function(options) {

        // deferAnimation is a wrapper function used to insert
        // any animations returned by fxn onto animationOption's
        // list of deferreds. This lets you chain complex
        // animations (see Exercises.nextCard).
        var deferAnimation = function(fxn) {
            return function(model, collection, options) {
                var result = fxn.call(this, model, collection, options);

                if (options && options.deferreds) {
                    options.deferreds.push(result);
                }

                return result;
            }
        };

        this.collection
            .bind("add", deferAnimation(function(card) {
                return this.animatePush(card);
            }), this)
            .bind("remove", deferAnimation(function() {
                return this.animatePop();
            }), this);

        return Backbone.View.prototype.initialize.call(this, options);
    },

    render: function() {

        var collectionContext = _.map(this.collection.models, function(card, index) {
            return this.viewContext(card, index);
        }, this);

        this.el.html(this.template({cards: collectionContext}));

        return this;

    },

    viewContext: function(card, index) {
        return _.extend( card.toJSON(), {
            index: index,
            frontVisible: this.options.frontVisible, 
            cid: card.cid,
            leaves: card.leaves()
        });
    },

    /**
     * Animate popping card off of stack
     */
    animatePop: function() {

        return this.el
            .find(".card-container")
                .first()
                    .slideUp(140, function() { $(this).remove(); });

    },

    /**
     * Animate pushing card onto head of stack
     */
    animatePush: function(card) {

        var context = this.viewContext(card, this.collection.length);

        return this.el
            .find(".stack")
                .prepend(
                    $(Templates.get("exercises.card")(context))
                        .css("display", "none")
                )
                .find(".card-container")
                    .first()
                        .delay(40)
                        .slideDown(140);

    }

});

/**
 * View of the single, currently-visible card
 */
Exercises.CurrentCardView = Backbone.View.extend({

    template: Templates.get("exercises.current-card"),

    model: null,

    leafEvents: ["change:done", "change:leavesEarned", "change:leavesAvailable"],

    initialize: function(options) {
        this.attachEvents();
        return Backbone.View.prototype.initialize.call(this, options);
    },

    attachEvents: function() {
        _.each(this.leafEvents, function(leafEvent) {
            this.model.bind(leafEvent, function() { this.updateLeaves(); }, this);
        }, this);
    },

    detachEvents: function() {
        _.each(this.leafEvents, function(leafEvent) {
            this.model.unbind(leafEvent);
        }, this);
    },

    /**
     * Renders the current card appropriately by card type.
     */
    render: function() {

        switch (this.model.get("cardType")) {

            case "problem":
                this.renderProblemCard();
                break;

            case "endofstack":
                this.renderEndOfStackCard();
                break;

            case "endofreview":
                this.renderEndOfReviewCard();
                break;

            default:
                throw "Trying to render unknown card type";

        }

        return this;
    },

    viewContext: function() {
        return _.extend( this.model.toJSON(), {
            leaves: this.model.leaves()
        });
    },

    /**
     * Renders the base card's structure, including leaves
     */
    renderCardContainer: function() {
        this.el.html(this.template(this.viewContext()));
    },

    /**
     * Renders the card's type-specific contents into contents container
     */
    renderCardContents: function(templateName, optionalContext) {

        var context = _.extend({}, this.viewContext(), optionalContext);

        this.el
            .find(".current-card-contents")
                .html(
                    $(Templates.get(templateName)(context))
                );

    },

    /**
     * Waits for API requests to finish, then runs target fxn
     */
    runAfterAPIRequests: function(fxn) {

        function tryRun() {
            if (Exercises.pendingAPIRequests > 0) {

                // Wait for any outbound API requests to finish.
                setTimeout(tryRun, 500);

            } else {

                // All API calls done, run target fxn
                fxn();

            }
        };

        tryRun();

    },

    renderCalculationInProgressCard: function() {
        this.renderCardContainer();
        this.renderCardContents("exercises.calculating-card");
    },

    /**
     * Renders a "calculations in progress" card, waits for API requests
     * to finish, and then renders the requested card template.
     */
    renderCardAfterAPIRequests: function(templateName, optionalContextFxn) {

        // Start off by showing the "calculations in progress" card...
        this.renderCalculationInProgressCard();

        // ...and wait a bit for dramatic effect before trying to show the
        // requested card.
        setTimeout(function() {
            Exercises.currentCardView.runAfterAPIRequests(function() {

                optionalContextFxn = optionalContextFxn || function(){};
                Exercises.currentCardView.renderCardContents(templateName, optionalContextFxn());

            });
        }, 2400);

    },

    /**
     * Renders a new card showing an exercise problem via khan-exercises
     */
    renderProblemCard: function() {

        // khan-exercises currently both generates content and hooks up
        // events to the exercise interface. This means, for now, we don't want 
        // to regenerate a brand new card when transitioning between exercise
        // problems.

        // TODO: in the future, if khan-exercises's problem generation is
        // separated from its UI events a little more, we can just rerender
        // the whole card for every problem.

        if (!$("#problemarea").length) {

            this.renderCardContainer();
            this.renderCardContents("exercises.problem-template");

            // Tell khan-exercises to setup its DOM and event listeners
            $(Exercises).trigger("problemTemplateRendered");

        }

        this.renderExerciseInProblemCard();

        // Update leaves since we may have not generated a brand new card
        this.updateLeaves();

    },

    renderExerciseInProblemCard: function() {

        var nextUserExercise = Exercises.BottomlessQueue.next();
        if (nextUserExercise) {
            // khan-exercises is listening and will fill the card w/ new problem contents
            $(Exercises).trigger("readyForNextProblem", {userExercise: nextUserExercise});
        }

    },

    /**
     * Renders a new card showing end-of-stack statistics
     */
    renderEndOfStackCard: function() {
        this.renderCardAfterAPIRequests("exercises.end-of-stack-card", function() { 
            return Exercises.completeStack.stats()
        });
    },

    /**
     * Renders a new card showing end-of-review statistics
     */
    renderEndOfReviewCard: function() {

        this.renderCalculationInProgressCard();

        // First wait for all API requests to finish
        this.runAfterAPIRequests(function() {

            var reviewsLeft = 0;

            // Then send another API request to see how many reviews are left --
            // and we'll change the end of review card's UI accordingly.
            $.ajax({
                url: "/api/v1/user/exercises/reviews/count",
                type: "GET",
                dataType: "json",
                success: function(data) { reviewsLeft = data; },
                complete: function() { Exercises.pendingAPIRequests--; }
            });
            Exercises.pendingAPIRequests++;

            // And finally wait for the previous API call to finish before
            // rendering end of review card.
            Exercises.currentCardView.renderCardAfterAPIRequests("exercises.end-of-review-card", function() { 
                // Pass reviews left info into end of review card
                return _.extend({}, Exercises.completeStack.stats(), {reviewsLeft: reviewsLeft});
            });

        });

    },

    /**
     * Update the currently available or earned leaves in current card's view
     */
    updateLeaves: function() {
        this.el
            .find(".leaves-container")
                .html(
                    $(Templates.get("exercises.card-leaves")(this.viewContext()))
                ); 

        if (this.model.get("done")) {

            $(".leaves-container").show();

            setTimeout(function() {
                $(".leaves-container .earned .full-leaf").addClass("animated");
            }, 1);

        } else {

            $(".leaves-container").hide();

        }
    },

    /**
     * Animate current card to right-hand completed stack
     */
    animateToRight: function() {
        this.el.addClass("shrinkRight");

        // These animation fxns explicitly return null as they are used in deferreds
        // and may one day have deferrable animations (CSS3 animations aren't
        // deferred-friendly).
        return null;
    },

    /**
     * Animate card from left-hand completed stack to current card
     */
    animateFromLeft: function() {
        this.el
            .removeClass("notransition")
            .removeClass("shrinkLeft");

        // These animation fxns explicitly return null as they are used in deferreds
        // and may one day have deferrable animations (CSS3 animations aren't
        // deferred-friendly).
        return null;
    },

    /**
     * Move (unanimated) current card from right-hand stack to left-hand stack between
     * toRight/fromLeft animations
     */
    moveLeft: function() {
        this.el
            .addClass("notransition")
            .removeClass("shrinkRight")
            .addClass("shrinkLeft");

        // These animation fxns explicitly return null as they are used in deferreds
        // and may one day have deferrable animations (CSS3 animations aren't
        // deferred-friendly).
        return null;
    }

});

Exercises.UserTopic = Backbone.Model.extend({

    defaults: {
        completeStack: [],
        incompleteStack: []
    },

    initialize: function(attributes, options) {
        // TODO(kamens): figure out the persistance model and hook 'er up
        return Backbone.Model.prototype.initialize.call(this, attributes, options);
    }

});

