var Goal = Backbone.Model.extend({
    defaults: {
        active: false,
        complete: false,
        progress: 0,
        title: "Unnamed goal",
        objectives: []
    },

    urlRoot: '/api/v1/user/goals',

    initialize: function() {
        // defaults for new models (e.g. not from server)
        // default created and updated values
        if (!this.has('created')) {
            var now = new Date().toISOString();
            this.set({created: now, updated: now});
        }

        // default progress value for all objectives
        _.each(this.get('objectives'), function(o) {
            if ( !o.progress ) {
                o.progress = 0;
            }
        });

        // a bunch of stuff needed to display goals in views. might need to be
        // refactored.
        this.calcDependents();

        this.bind('change', this.fireCustom, this);
    },

    calcDependents: function() {
        var progress = this.calcTotalProgress(this.get('objectives'));
        var objectiveWidth = 100/this.get('objectives').length;
        _.each(this.get('objectives'), function (obj) {
            Goal.calcObjectiveDependents(obj, objectiveWidth);
        });
        this.set({
            progress: progress,
            progressStr: Goal.floatToPercentageStr(progress),
            complete: progress >= 1,

            // used to display 3/5 in goal summary area
            objectiveProgress: _.filter(this.get('objectives'), function(obj) {
                return obj.progress >= 1;
            }).length,

            // used to maintain sorted order in a GoalCollection
            updatedTime: new Date(this.get('updated')).getTime()
        }, {silent: true});
    },

    calcTotalProgress: function(objectives) {
        objectives = objectives || this.get('objectives');
        var progress = 0;
        if (objectives.length) {
            progress = _.reduce(objectives, function(p, ob) { return p + ob.progress; }, 0);
            if ( objectives.length > 0 ) {
                progress = progress/objectives.length;
            } else {
                progress = 0;
            }
        }
        return progress;
    },

    fireCustom: function() {
        this.calcDependents();

        if (this.hasChanged('progress')) {
            // we want to fire these events after all other listeners to 'change'
            // have had a chance to run
            var toFire = [];

            // check for goal completion
            if (this.get('progress') >= 1) {
                toFire.push(['goalcompleted', this]);
            }
            else {
                // now look for updated objectives
                oldObjectives = this.previous('objectives');
                _.each(this.get('objectives'), function(newObj, i) {
                    var oldObj = oldObjectives[i];
                    if (newObj.progress > oldObj.progress) {
                        toFire.push(['progressed', this, newObj]);
                        if (newObj.progress >= 1) {
                            toFire.push(['completed', this, newObj]);
                        }
                    }
                }, this);
            }
            if ( _.any(toFire) ) {
                // register a callback to execute at the end of the rest of the
                // change callbacks
                this.collection.bind('change', function callback() {
                    // this callback should only run once, so immediately unbind
                    this.unbind('change', callback);
                    // trigger all change notifications
                    _.each(toFire, function(triggerArgs) {
                        this.trigger.apply(this, triggerArgs);
                    }, this);
                }, this.collection);
            }
        }
    }
}, {
    calcObjectiveDependents: function(objective, objectiveWidth) {
        objective.complete = objective.progress >= 1;
        objective.progressStr = Goal.floatToPercentageStr(objective.progress);
        objective.iconFillHeight = Goal.calcIconFillHeight(objective);
        objective.objectiveWidth = objectiveWidth;
        objective.isVideo = (objective.type == 'GoalObjectiveWatchVideo');
        objective.isAnyVideo = (objective.type == 'GoalObjectiveAnyVideo');
        objective.isExercise = (objective.type == 'GoalObjectiveExerciseProficiency');
        objective.isAnyExercise = (objective.type == 'GoalObjectiveAnyExerciseProficiency');
    },

    calcIconFillHeight: function(objective) {
        var height = objective.type.toLowerCase().indexOf("exercise") >= 1 ? 13 : 12;
        var offset = objective.type.toLowerCase().indexOf("exercise") >= 1 ? 4 : 6;
        return Math.ceil(objective.progress * height) + offset;
    },

    floatToPercentageStr: function(progress) {
        return (progress * 100).toFixed(0);
    }
});

var GoalCollection = Backbone.Collection.extend({
    model: Goal,

    initialize: function() {
        this.updateActive();

        // ensure updateActive is called whenever the collection changes
        this.bind('add', this.updateActive, this);
        this.bind('remove', this.updateActive, this);
        this.bind('reset', this.updateActive, this);
    },

    url: '/api/v1/user/goals',

    comparator: function(goal) {
        // display most recently updated goal at the top of the list.
        // http://stackoverflow.com/questions/5636812/sorting-strings-in-reverse-order-with-backbone-js/5639070#5639070
        return -goal.get("updatedTime");
    },

    active: function(goal) {
        var current = this.find(function(g) {return g.get('active');}) || null;
        if (goal && goal !== current) {
            // set active
            if (current !== null) {
                current.set({active: false});
            }
            goal.set({active: true});
            current = goal;
        }
        return current;
    },

    updateActive: function() {
        this.active(this.findActiveGoal());
    },

    incrementalUpdate: function(updatedGoals) {
        _.each(updatedGoals, function(newGoal) {
            oldGoal = this.get(newGoal.id) || null;

            if (oldGoal !== null) {
                oldGoal.set(newGoal);
            }
            else {
                // todo: remove this, do something better
                console.log("Error: brand new goal appeared from somewhere", newGoal);
            }
        }, this);
    },

    findGoalWithObjective: function(internalId, specificType, generalType) {
        return this.find(function(goal) {
            // find a goal with an objective for this exact entity
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == specificType && internalId == ob.internal_id;
            });
        }) || this.find(function(goal) {
            // otherwise find a goal with any entity proficiency
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == generalType;
            });
        }) || null;
    },

    // find the most appriate goal to display for a given URL
    findActiveGoal: function() {
        var matchingGoal = null;

        if (window.location.pathname.indexOf("/exercise") === 0 &&
                typeof userExercise !== 'undefined') {
            matchingGoal = this.findGoalWithObjective(userExercise.exercise,
                'GoalObjectiveExerciseProficiency',
                'GoalObjectiveAnyExerciseProficiency');
        } else if (window.location.pathname.indexOf("/video") === 0 &&
                 typeof Video.readableId !== 'undefined') {
            matchingGoal = this.findGoalWithObjective(Video.readableId,
                "GoalObjectiveWatchVideo", "GoalObjectiveAnyVideo");
        }

        // if we're not on a matching exercise or video page, just show the
        // most recently upated one
        if (matchingGoal === null) {
            matchingGoal = this.at(0); // comparator is most recently updated
        }

        return matchingGoal;
    }
});

var GoalBookView = Backbone.View.extend({
    template: Templates.get( "shared.goalbook" ),
    isVisible: false,
    needsRerender: true,

    initialize: function() {
        $(this.el)
            .delegate('.close-button', 'click', $.proxy(this.hide, this))

            // listen to archive button on goals
            .delegate('.goal.recently-completed', 'mouseenter mouseleave', function( e ) {
                var el = $(e.currentTarget);
                if ( e.type == 'mouseenter' ) {
                    el.find(".goal-description .summary-light").hide();
                    el.find(".goal-description .archive").show();
                } else {
                    el.find(".goal-description .archive").hide();
                    el.find(".goal-description .summary-light").show();
                }
            })

            .delegate('.archive', 'click', $.proxy(function( e ) {
                var el = $(e.target).closest('.goal');
                this.animateGoalToHistory(el);
                // todo: remove model
            }, this))

            .delegate( '.new-goal', 'click', $.proxy(function( e ) {
                e.preventDefault();
                this.hide();
                newGoalDialog.show();
            }, this));

        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
        this.model.bind('remove', this.render, this);
        this.model.bind('add', this.added, this);
        this.model.bind('goalcompleted', this.show, this);
    },

    show: function() {
        this.isVisible = true;

        // render if necessary
        if (this.needsRerender) {
            this.render();
        }

        var that = this;
        // animate on the way down
        return $(this.el).slideDown("fast", function() {
            // listen for escape key
            $(document).bind('keyup.goalbook', function ( e ) {
                if ( e.which == 27 ) {
                    that.hide();
                }
            });

            // close the goalbook if user clicks elsewhere on page
            $('body').bind('click.goalbook', function( e ) {
                if ( $(e.target).closest('#goals-nav-container').length === 0 ) {
                    that.hide();
                }
            });
        });
    },

    hide: function() {
        this.isVisible = false;
        $(document).unbind('keyup.goalbook');
        $('body').unbind('click.goalbook');

        // if there are completed goals, move them to history before closing
        var completed = this.model.filter(function(goal) { return goal.get('complete'); });

        var completedEls = this.$('.recently-completed');
        if ( completedEls.length > 0 ) {
            this.animateThenHide(completedEls);
        } else {
            return $(this.el).slideUp("fast");
        }
    },

    added: function(goal, options) {
        this.needsRerender = true;
        this.show();
        // add a highlight to the new goal
        $(".goal[data-id=" + goal.get('id') + "]").effect('highlight', {}, 2500);
    },

    animateThenHide: function(els) {
        // wait for the animation to complete and then close the goalbook
        this.animateGoalToHistory(els).then($.proxy(function() {
           $(this.el).slideUp("fast");
       }, this));
    },

    render: function() {
        var jel = $(this.el);
        // delay rendering until the view is actually visible
        if ( !this.isVisible ) {
            this.needsRerender = true;
        }
        else {
            console.log("rendering GoalBookView", this);
            this.needsRerender = false;
            var json = _.pluck(this.model.models, 'attributes');
            jel.html(this.template({goals: json}));
        }
        return jel;
    },

    animateGoalToHistory: function(els) {
        var btnGoalHistory = this.$('#btn-goal-history');

        var promises = $(els).map(function(i, el) {
            var dfd = $.Deferred();
            var jel = $(el);
            jel .children()
                    .each(function () {
                        $(this).css('overflow', 'hidden').css('height', $(this).height());
                    })
                .end()
                .delay(500)
                .animate({
                    width: btnGoalHistory.width(),
                    left: btnGoalHistory.position().left
                })
                .animate({
                        top: btnGoalHistory.position().top - jel.position().top,
                        height: '0',
                        opacity: 'toggle'
                    },
                    'easeInOutCubic',
                    function() {
                        $(this).remove();
                        dfd.resolve();
                    }
                );
            return dfd.promise();
        }).get();

        // once all the animations are done, make the history button glow
        var button = $.Deferred();
        $.when.apply(null, promises).then(function() {
            btnGoalHistory
                .animate({backgroundColor: 'orange'})
                .animate({backgroundColor: '#ddd'}, button.resolve);
        });

        // return a promise that the history button is done animating
        return button.promise();
    }
});

var GoalSummaryView = Backbone.View.extend({
    template: Templates.get( "shared.goal-summary-area" ),

    initialize: function(args) {
        $(this.el).delegate('#goals-drawer', 'click',
            $.proxy(args.goalBookView.show, args.goalBookView));

        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
        this.model.bind('remove', this.render, this);
        this.model.bind('add', this.render, this);
        this.model.bind('completed', this.justFinishedObjective, this);
    },

    render: function() {
        console.log("rendering GoalSummaryView", this);
        var active = this.model.active() || null;
        if (active !== null) {
            $(this.el).html(this.template(active.attributes));
        }
        else {
            // todo: put create a goal button here?
            $(this.el).empty();
        }
        return this;
    },

    justFinishedObjective: function(newGoal, newObj) {
        this.render();
        this.$('#goals-drawer').effect('highlight', {}, 2500);
    }
});


var NewGoalView = Backbone.View.extend({
    template: Templates.get( 'shared.goal-new' ),

    initialize: function() {
        // this View assumes the element is pre-rendered, so automatically
        // hookup events
        this.hookup();
    },

    hookup: function() {
        $(this.el)
            .delegate( ".newgoal.custom", "click", $.proxy(this.createCustomGoal, this))
            .delegate( ".newgoal.five_exercises", "click", $.proxy(function(e) {
                e.preventDefault();
                this.createSimpleGoal("five_exercises");
            }, this))
            .delegate( ".newgoal.five_videos", "click", $.proxy(function(e) {
                e.preventDefault();
                this.createSimpleGoal("five_videos");
            }, this));

        var that = this;
        this.$('.newgoal').hoverIntent(
            function hfa( evt ){
                that.$( ".newgoal" ).not( this ).hoverFlow( evt.type, { opacity : 0.2}, 750, "easeInOutCubic" );
                $( ".info.pos-left", this ).hoverFlow( evt.type, { left : "+=30px", opacity : "show" }, 350, "easeInOutCubic" );
                $( ".info.pos-right, .info.pos-top", this ).hoverFlow( evt.type, { right : "+=30px", opacity : "show" }, 350, "easeInOutCubic" );
            },
            function hfo( evt ) {
                that.$( ".newgoal" ).not( this ).hoverFlow( evt.type, { opacity : 1}, 175, "easeInOutCubic" );
                $( ".info.pos-left", this).hoverFlow( evt.type, { left : "-=30px", opacity : "hide" }, 150, "easeInOutCubic" );
                $( ".info.pos-right, .info.pos-top", this).hoverFlow( evt.type, { right : "-=30px", opacity : "hide" }, 150, "easeInOutCubic" );
            }
        );
    },

    createSimpleGoal: function( selectedType ) {
        var goal;
        if ( selectedType == 'five_exercises' ) {
            goal = new Goal({
                title: "Complete Five Exercises",
                objectives: [
                    { description: "Any exercise", type: "GoalObjectiveAnyExerciseProficiency" },
                    { description: "Any exercise", type: "GoalObjectiveAnyExerciseProficiency" },
                    { description: "Any exercise", type: "GoalObjectiveAnyExerciseProficiency" },
                    { description: "Any exercise", type: "GoalObjectiveAnyExerciseProficiency" },
                    { description: "Any exercise", type: "GoalObjectiveAnyExerciseProficiency" }
                ]
            });
        } else if ( selectedType == "five_videos" ) {
            goal = new Goal({
                title: "Complete Five Videos",
                objectives: [
                    { description: "Any video", type: "GoalObjectiveAnyVideo" },
                    { description: "Any video", type: "GoalObjectiveAnyVideo" },
                    { description: "Any video", type: "GoalObjectiveAnyVideo" },
                    { description: "Any video", type: "GoalObjectiveAnyVideo" },
                    { description: "Any video", type: "GoalObjectiveAnyVideo" }
                ]
            });
        }

        this.model.add(goal);
        goal.save().fail($.proxy(function() {
            console.log("Error happened when saving new custom goal", goal);
            this.model.remove(goal);
        }, this));
        this.trigger("creating");
    },

    createCustomGoal: function( e ) {
        this.trigger("creating");
        e.preventDefault();
        globalPopupDialog.show('create-custom-goal', null, 'Create a custom goal',
            $("#generic-loading-dialog").html(), false);
        $.ajax({
            url: "/goals/new?need_maps_package=" + (!window.KnowledgeMap ? "true" : "false"),
            type: 'GET',
            dataType: 'html',
            success: function(html) {
                if (globalPopupDialog.visible) {
                    globalPopupDialog.show('create-custom-goal', null, 'Create a custom goal', html, false);
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $("#generic-loading-message").html('Page load failed. Please try again.');
            }
        });
    }
});

var NewGoalDialog = Backbone.View.extend({
    template: Templates.get( "shared.goal-new-dialog" ),

    initialize: function() {
        this.render();
        this.model.bind('add', this.hide, this);
    },

    render: function() {
        this.el = $(this.template()).appendTo(document.body).get(0);
        this.newGoalView = new NewGoalView({
            el: this.$('.goalpicker'),
            model: this.model
        });
        this.newGoalView.bind('creating', this.hide, this);
        return this;
    },

    show: function() {
        $(this.el)
            .modal({
                keyboard: true,
                backdrop: true,
                show: true
            });
    },

    hide: function() {
        $(this.el).modal('hide');
    }
});

$(function() {
    window.GoalBook = new GoalCollection(window.GoalsBootstrap || []);
    APIActionResults.register( "updateGoals",
        $.proxy(GoalBook.incrementalUpdate, window.GoalBook) );

    window.myGoalBookView = new GoalBookView({
        el: "#goals-nav-container",
        model: GoalBook
    });
    window.myGoalSummaryView = new GoalSummaryView({
        el: "#goals-container",
        model: GoalBook,
        goalBookView: myGoalBookView
    });

    myGoalSummaryView.render();
    window.newGoalDialog = new NewGoalDialog({model: GoalBook});
});

// todo: should we do this globally?
Handlebars.registerPartial('goal-objectives', Templates.get( "shared.goal-objectives" ));
Handlebars.registerPartial('goalbook-row', Templates.get( 'shared.goalbook-row' ));
Handlebars.registerPartial('goal-new', Templates.get( "shared.goal-new" ));
