var calcIconFillHeight = function(o) {
    var height = o.type.toLowerCase().indexOf("exercise") >= 1 ? 13 : 12;
    var offset = o.type.toLowerCase().indexOf("exercise") >= 1 ? 4 : 6;
    return Math.ceil(o.progress * height) + offset;
};

var calcObjectiveDependents = function(objective, objectiveWidth) {
    objective.complete = objective.progress >= 1;
    objective.progress_str = (objective.progress * 100).toFixed(0);
    objective.iconFillHeight = calcIconFillHeight(objective);
    objective.objectiveWidth = objectiveWidth;
    objective.isVideo = (objective.type == 'GoalObjectiveWatchVideo');
    objective.isAnyVideo = (objective.type == 'GoalObjectiveAnyVideo');
    objective.isExercise = (objective.type == 'GoalObjectiveExerciseProficiency');
    objective.isAnyExercise = (objective.type == 'GoalObjectiveAnyExerciseProficiency');
};

var Goal = Backbone.Model.extend({
    defaults: {
        active: false,
        complete: false,
        progress: 0,
        title: "Unnamed goal",
        objectives: []
    },

    initialize: function() {
        this.calcDependents();
        this.bind('change', this.fireCustom, this);
    },

    calcDependents: function() {
        var progress = this.calcTotalProgress(this.get('objectives'));
        var objectiveWidth = 100/this.get('objectives').length;
        _.each(this.get('objectives'), function (obj) {
            calcObjectiveDependents(obj, objectiveWidth);
        });
        this.set({
            progress: progress,
            progressStr: (progress * 100).toFixed(0),
            complete: progress >= 1,
            objectiveProgress: _.filter(this.get('objectives'), function(obj) {
                return obj.progress >= 1;
            }).length
        }, {silent: true});
    },

    calcTotalProgress: function(objectives) {
        objectives = objectives || this.get('objectives');
        var progress = 0;
        if (objectives.length) {
            var count = 0;
            $.each(objectives, function(i, ob) {
                progress += ob.progress;
            });
            progress = progress/objectives.length;
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

    comparator: function(goal) {
        return goal.get("updated");
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

    findExerciseObjectiveFor: function(url) {
        var matchingGoal = null;

        var getExerciseId = function(url) {
            var regex = /\/exercise\/([^\/?]+)/;
            var matches = url.match(regex);
            return matches ? matches[1] : '';
        };

        var exerciseId = getExerciseId(url);
        // find a goal with exactly this exercise
        matchingGoal = this.find(function(goal) {
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == "GoalObjectiveExerciseProficiency" &&
                    exerciseId == getExerciseId(ob.url);
            });
        }) || null;

        if ( matchingGoal === null ) {
            // find an exercise process goal
            matchingGoal = this.find(function(goal) {
                return _.find(goal.get('objectives'), function(ob) {
                    return ob.type == "GoalObjectiveAnyExerciseProficiency";
                });
            }) || null;
        }

        return matchingGoal;
    },

    findVideoObjectiveFor: function(url) {
        var matchingGoal = null;

        var getVideoId = function(url) {
            var regex = /\/video\/([^\/?]+)/;
            var matches = url.match(regex);
            return matches ? matches[1] : '';
        };

        var videoId = getVideoId(url);

        // find a goal with exactly this exercise
        matchingGoal = this.find(function(goal) {
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == "GoalObjectiveWatchVideo" &&
                    videoId == getVideoId(ob.url);
            });
        }) || null;

        if (matchingGoal === null) {
            // find an exercise process goal
            matchingGoal = this.find(function(goal) {
                return _.find(goal.get('objectives'), function(ob) {
                    return ob.type == "GoalObjectiveAnyVideo";
                });
            }) || null;
        }

        return matchingGoal;
    },

    // find the most appriate goal to display for a given URL
    findActiveGoal: function() {
        var matchingGoal = null;
        var url = window.location.toString();

        if (window.location.pathname.indexOf("/exercise") === 0) {
            matchingGoal = this.findExerciseObjectiveFor(url);
            if (matchingGoal !== null) {
                console.log('found a matching exercise goal');
            }
        }
        else if (window.location.pathname.indexOf("/video") === 0) {
            matchingGoal = this.findVideoObjectiveFor(url);
            if (matchingGoal !== null) {
                console.log('found a matching video goal');
            }
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
            .delegate('.hide-goals', 'click', $.proxy(this.hide, this))

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
            }, this));

        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
        this.model.bind('remove', this.render, this);
        this.model.bind('add', this.added, this);
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
        console.log('completed:', completedEls);
        if ( completedEls.length > 0 ) {
            this.animateThenHide(completedEls);
        } else {
            return $(this.el).slideUp("fast");
        }
    },

    added: function(goal) {
        this.render();

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

// should probably do this for all templates
Handlebars.registerPartial('goalbook-row', Templates.get( 'shared.goalbook-row' ));

var GoalSummaryView = Backbone.View.extend({
    template: Templates.get( "shared.goal-summary-area" ),

    initialize: function(args) {
        $(this.el).delegate('#goals-drawer', 'click',
            $.proxy(args.goalBook.show, args.goalBook));

        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
        this.model.bind('remove', this.render, this);
        this.model.bind('add', this.render, this);
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
    }
});

var justFinishedObjective = function(newGoal, newObj) {
    console.log("Just finished objective", newObj);
    $("#goals-congrats").text('Just finished objective!').show().fadeOut(3000);
};

var justFinishedGoal = function(goal) {
    console.log("Just finished goal", goal);
    myGoalBookView.show();
};

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
        goalBook: myGoalBookView
    });

    myGoalSummaryView.render();
    GoalBook.bind('completed', justFinishedObjective);
    GoalBook.bind('goalcompleted', justFinishedGoal);
});

var requestGoals = function() {
    $.ajax({ url: "/api/v1/user/goals/current", success: updateGoals });
};
var updateGoals = function(goals) {
    GoalBook.reset(goals);
};

var predefinedGoalsList = {
    "five_exercises" : {
        "title": "Complete Five Exercises",
        "objective1_type": "GoalObjectiveAnyExerciseProficiency",
        "objective2_type": "GoalObjectiveAnyExerciseProficiency",
        "objective3_type": "GoalObjectiveAnyExerciseProficiency",
        "objective4_type": "GoalObjectiveAnyExerciseProficiency",
        "objective5_type": "GoalObjectiveAnyExerciseProficiency"
    },
    "five_videos" : {
        "title": "Watch Five Videos",
        "objective1_type": "GoalObjectiveAnyVideo",
        "objective2_type": "GoalObjectiveAnyVideo",
        "objective3_type": "GoalObjectiveAnyVideo",
        "objective4_type": "GoalObjectiveAnyVideo",
        "objective5_type": "GoalObjectiveAnyVideo"
    }
};

var createSimpleGoalDialog = {
    showDialog: function() {
        myGoalBookView.hide();
        globalPopupDialog.show('create-goal', [350,280], 'Set a new learning goal', $("#goal-create-dialog").html(), true);
    },
    hideDialog: function() {
        globalPopupDialog.hide();
    },

    createSimpleGoal: function() {
        var selected_type = $("#popup-dialog")
            .find("input[name=\"goal-type\"]:checked").val();
        var goal = predefinedGoalsList[selected_type];
        var prevButtonHtml = $("#create-simple-goal-button").html();

        $('#create-simple-goal-error').html('');
        $("#create-simple-goal-button").html("<a class='simple-button action-gradient'><img src='/images/throbber.gif' class='throbber'/><span style='margin-left: 20px'>Adding goal... </span></a>");
        $.ajax({
            url: "/api/v1/user/goals/create",
            type: 'POST',
            dataType: 'json',
            data: $.param(goal),
            success: function(json) {
                createSimpleGoalDialog.goalCreationComplete(json);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $('#create-simple-goal-error').html('Goal creation failed');
                $("#create-simple-goal-button").html(prevButtonHtml);
            }
        });
    },
    createCustomGoal: function() {
        globalPopupDialog.show('create-custom-goal', null, 'Create a custom goal', $("#generic-loading-dialog").html(), false);
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
    },
    goalCreationComplete: function(goal) {
        createSimpleGoalDialog.hideDialog();
        GoalBook.add(goal);
        console.log("Created goal");
        myGoalBookView.show();
        if (window.Profile)
            window.Profile.showGoalType('current');
    }
};

Handlebars.registerPartial('goal-objectives', Templates.get( "shared.goal-objectives" )); // TomY TODO do this automatically?
