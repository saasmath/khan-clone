var calcIconFillHeight = function(o) {
    var height = o.type.toLowerCase().indexOf("exercise") >= 1 ? 13 : 12;
    var offset = o.type.toLowerCase().indexOf("exercise") >= 1 ? 4 : 6;
    return Math.ceil(o.progress * height) + offset;
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
        _.each(this.get('objectives'), function (obj) {
            obj.complete = obj.progress >= 1;
            obj.iconFillHeight = calcIconFillHeight(obj);
        });
        this.set({
            progress: progress,
            progressStr: (progress * 100).toFixed(0),
            complete: progress >= 1,
            objectiveProgress: _.filter(this.get('objectives'), function(obj) {
                return obj.progress >= 1;
            }).length,
            objectiveWidth: 100/this.get('objectives').length
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

        var exid = parseQueryString(url).exid;
        // find a goal with exactly this exercise
        matchingGoal = this.find(function(goal) {
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == "GoalObjectiveExerciseProficiency" &&
                    exid == parseQueryString(ob.url).exid;
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
            return matches[1];
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

        if (window.location.pathname == "/exercises") {
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
    template: Templates.get( "goalbook" ),
    isVisible: false,
    needsRerender: true,

    initialize: function() {
        $(this.el).delegate('.hide-goals', 'click', $.proxy(this.hide, this));

        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
        this.model.bind('remove', this.render, this);
        this.model.bind('add', this.render, this);
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
        return $(this.el).slideUp("fast");
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
    }
});

// should probably do this for all templates
Handlebars.registerPartial('goalbook-row', Templates.get( 'goalbook-row' ));

var GoalSummaryView = Backbone.View.extend({
    template: Templates.get( "goal-summary-area" ),

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
    var recentlyCompleted = $('.recently-completed');
    animateGoalTpHistory(recentlyCompleted);
    //todo - also remove the goal from the model
};

var animateGoalToHistory = function(el) {
    var btnGoalHistory = $('#btn-goal-history');
    el  .children()
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
                top: btnGoalHistory.position().top - el.position().top,
                height: '0',
                opacity: 'toggle'
            },
            'easeInOutCubic',
            function () {
                $(this).remove();
                $('#btn-goal-history')
                    .animate({backgroundColor: 'orange'})
                    .animate({backgroundColor: '#ddd'});
            }
        );
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

// todo: surely this belongs in a library somewhere?
var parseQueryString = function(url) {
    var querystring = decodeURIComponent(url.substring(url.indexOf('?')+1));
    var pairs = querystring.split('&');
    var qs = {};
    var qslist = $.each(pairs, function(i, pair) {
        var kv = pair.split("=");
        qs[kv[0]] = kv[1];
    });
    return qs;
};

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
        $("#popup-dialog").html($("#goal-create-dialog").html());
    },
    hideDialog: function() {
        $("#popup-dialog").html('');
    },
    createSimpleGoal: function() {
        var selected_type = $("#goal-popup-dialog")
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
                createSimpleGoalDialog.hideDialog();
                GoalBook.add(json);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $('#create-simple-goal-error').html('Goal creation failed');
                $("#create-simple-goal-button").html(prevButtonHtml);
            }
        });
    },
    createCustomGoal: function() {
        $("#popup-dialog").html($("#custom-goal-loading-dialog").html());
        $.ajax({
            url: "/goals/new?need_maps_package=" + (!window.KnowledgeMap ? "true" : "false"),
            type: 'GET',
            dataType: 'html',
            success: function(html) {
                $("#popup-dialog").html(html);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $("#custom-goal-loading-message").html('Page load failed. Please try again.');
            }
        });
    }
};

function goalCreateViewModel(goalModel) {
    var goalViewModel = $.extend({}, goalModel);

    goalViewModel.objectiveWidth = 100/goalModel.objectives.length;

    $.each(goalViewModel.objectives, function(idx2, objective) {
        objective.progressPercentage = (objective.progress*100).toFixed(0);

        objective.statusCSS = objective.status ? objective.status : "not-started";

        if (objective.type == 'GoalObjectiveExerciseProficiency' || objective.type == 'GoalObjectiveAnyExerciseProficiency')
            objective.typeCSS = 'exercise';
        else if (objective.type == 'GoalObjectiveWatchVideo' || objective.type == 'GoalObjectiveAnyVideo')
            objective.typeCSS = 'video';
    });

    return goalViewModel;
}
