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

        var speedyCards = this.filter(function(card) {
            return card.get("leavesEarned") >= 4;
        }).length;
            
        return {
            "longestStreak": longestStreak,
            "speedyCards": speedyCards,
            "totalLeaves": totalLeaves
        };
    }

});

/**
 * StackCollection that is automatically cached in localStorage when modified
 * and loads itself from cache on initialization.
 */
Exercises.CachedStackCollection = Exercises.StackCollection.extend({

    sessionId: null,

    initialize: function(models, options) {

        this.sessionId = options ? options.sessionId : null;

        if (!this.sessionId) {
            throw "Must supply a unique sessionId for any stack being cached";
        }

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
            this.sessionId
        ].join(":");
    },

    loadFromCache: function() {

        var modelAttrs = LocalStore.get(this.cacheKey());
        if (modelAttrs) {

            _.each(modelAttrs, function(attrs) {
                this.add(new Exercises.Card(attrs))
            }, this);

        }

    },

    cache: function() {
        LocalStore.set(this.cacheKey(), this.models);
    },

    /**
     * Delete this stack from localStorage
     */
    clearCache: function() {
        LocalStore.del(this.cacheKey());
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
                    .slideUp(360, function() { $(this).remove(); });

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
                        .css("opacity", 0)
                )
                .find(".card-container")
                    .first()
                        .delay(50)
                        .slideDown(200)
                        .animate(
                            { opacity: 1 },
                            { queue: false, duration: 140 }
                        );

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

        // Animate the first 8 cards into place -- others just go away
        setTimeout(function() {

            $(".complete-stack .card-container").each(function(ix, el) {
                if (ix < 8) {
                    $(el).addClass("into-pocket").addClass("into-pocket-" + ix);
                } else {
                    $(el).css("display", "none");
                }
            });

        }, 500);

        // Fade in/out our various pieces of "calculating progress" text
        var fadeInNextText = function(jel) {

            if (!jel || !jel.length) {
                jel = $(".current-card-contents .calc-text-spin span").first();
            }

            jel.fadeIn(600, function() {
                jel.delay(1000).fadeOut(600, function() {
                    fadeInNextText(jel.next("span"));
                });
            })
        };

        fadeInNextText();

   },

    /**
     * Renders a "calculations in progress" card, waits for API requests
     * to finish, and then renders the requested card template.
     */
    renderCardAfterAPIRequests: function(templateName, optionalContextFxn, optionalCallbackFxn) {

        // Start off by showing the "calculations in progress" card...
        this.renderCalculationInProgressCard();

        // ...and wait a bit for dramatic effect before trying to show the
        // requested card.
        setTimeout(function() {
            Exercises.currentCardView.runAfterAPIRequests(function() {

                optionalContextFxn = optionalContextFxn || function(){};
                Exercises.currentCardView.renderCardContents(templateName, optionalContextFxn());

                if (optionalCallbackFxn) {
                    optionalCallbackFxn();
                }

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
        this.renderCardAfterAPIRequests(
            "exercises.end-of-stack-card",
            function() { 
                return _.extend(Exercises.sessionStats.progressStats(), Exercises.completeStack.stats());
            },
            function() {
                $(Exercises.completeStackView.el).hide();
            }
        );
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

    attachLeafTooltip: function() {
        $(this).qtip({
            content: {
                text: $(this).data("desc")
            },
            style: {
                classes: "ui-tooltip-light leaf-tooltip"
            },
            position: {
                my: "bottom center",
                at: "top center"
            },
            show: {
                delay: 0,
                effect: {
                    length: 0
                }
            },
            hide: {
                delay: 0
            }
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
                )
                .find(".leaf")
                    .each(this.attachLeafTooltip);

        if (this.model.get("done")) {

            $(".leaves-container").show();
            //TODO: This probably doesn't belong here
            $(".current-card").addClass("done");

            setTimeout(function() {
                $(".leaves-container .earned .full-leaf").addClass("animated");
            }, 1);

        } else {

            $(".current-card").removeClass("done");

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

/**
 * SessionStats stores and caches a list of interesting statistics
 * about each individual stack session.
 */
Exercises.SessionStats = Backbone.Model.extend({

    sessionId: null,

    initialize: function(attributes, options) {

        this.sessionId = options ? options.sessionId : null;

        if (!this.sessionId) {
            throw "Must supply a unique sessionId for any stack stats being cached";
        }

        // Try to load stats from cache
        this.loadFromCache();

        // Update exercise stats any time new exercise data is cached locally
        $(Exercises).bind("newUserExerciseData", $.proxy(function(ev, data) {
            this.updateProgressStats(data.exerciseName);
        }, this));

        return Backbone.Model.prototype.initialize.call(this, attributes, options);
    },

    cacheKey: function() {
        return [
            "cachedsessionstats",
            this.sessionId
        ].join(":");
    },

    loadFromCache: function() {
        var attrs = LocalStore.get(this.cacheKey());
        if (attrs) {
            this.set(attrs);
        }
    },

    cache: function() {
        LocalStore.set(this.cacheKey(), this.attributes);
    },

    clearCache: function() {
        LocalStore.del(this.cacheKey());
    },

    /**
     * Update the start/end/change progress for this specific exercise so we
     * can summarize the user's session progress at the end of a stack.
     */
    updateProgressStats: function(exerciseName) {

        var userExercise = Exercises.BottomlessQueue.userExerciseCache[exerciseName];

        if (userExercise) {

            /** 
             * For now, we're just keeping track of the change in progress per
             * exercise
             * Converting manually from decimal to % so it can be more easily used in
             * HTML/CSS land.
             */
            var progressStats = this.get("progress") || {},

                stat = progressStats[exerciseName] || {
                    displayName: userExercise.exerciseModel.displayName,
                    startTotalDone: userExercise.totalDone,
                    start: userExercise.progress * 100
                };

            stat.endTotalDone = userExercise.totalDone;
            stat.end = userExercise.progress * 100;
            stat.change = stat.end - stat.start;

            // Set and cache the latest
            progressStats[exerciseName] = stat;
            this.set({"progress": progressStats});
            this.cache();

        }

    },

    /**
     * Return list of stat objects for only those exercises which had at least
     * one problem done during this session.
     */
    progressStats: function() {
        return { progress: 
            _.filter(
                    _.values(this.get("progress") || {}),
                    function(stat) {
                        return stat.endTotalDone && stat.endTotalDone > stat.startTotalDone;
                    }
            )
        };
    }

});

