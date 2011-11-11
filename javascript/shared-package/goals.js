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
        this.set({
            progress: progress,
            progressStr: (progress * 100).toFixed(0),
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
        if (this.hasChanged('progress')) {
            // inspect old element to see what changed, fire events
            //this.trigger('progressed');
            justWorkedOnGoal(this);
            // check for goal completion

            // check to see if we just finished the goal
            if (this.get('progress') >= 1) {
                //this.trigger('completed');
                justFinishedGoal(this);
            }
            else {
                // now look for updated objectives
                oldObjectives = this.previous('objectives');
                var goal = this;
                _.each(this.get('objectives'), function(newObj, i) {
                    var oldObj = oldObjectives[i];
                    if (newObj.progress > oldObj.progress) {
                        justWorkedOnObjective(goal, newObj);
                        if (newObj.progress >= 1) {
                            justFinishedObjective(goal, newObj);
                        }
                    }
                });
            }
        }
    }
});

var GoalCollection = Backbone.Collection.extend({
    model: Goal,
    _active: null,

    initialize: function() {
        this.updateActive();
    },

    comparator: function(goal) {
        return goal.get("updated");
    },

    active: function(goal) {
        if (goal && goal !== this._active) {
            // set active
            if (this._active) {
                this._active.set({active: false});
            }
            this._active = goal;
            this._active.set({active: true});
        }
        return this._active;
    },

    updateActive: function() {
        var url = window.location.toString();
        this.active(GoalCollection.findMatchingGoalFor(url, this));
    },

    // override reset so that updateActive is called before the reset event fires
    reset: function(models, options) {
        options = options || {};
        var silentOptions = _.extend({}, options, {silent: true});
        Backbone.Collection.prototype.reset.call(this, models, silentOptions);
        this.updateActive();
        if (!options.silent) this.trigger('reset', this, options);
    }
}, { // class properties:

    // todo: cleanup window.location stuff in here!
    findExerciseObjectiveFor: function(url, goals) {
        var matchingGoal = null;

        var exid = parseQueryString(url).exid;
        // find a goal with exactly this exercise
        matchingGoal = goals.find(function(goal) {
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == "GoalObjectiveExerciseProficiency" &&
                    exid == parseQueryString(ob.url).exid;
            });
        }) || null;

        if ( matchingGoal === null ) {
            // find an exercise process goal
            matchingGoal = goals.find(function(goal) {
                return _.find(goal.get('objectives'), function(ob) {
                    return ob.type == "GoalObjectiveAnyExerciseProficiency";
                });
            }) || null;
        }

        return matchingGoal;
    },

    findVideoObjectiveFor: function(url, goals) {
        var matchingGoal = null;

        var getVideoId = function(url) {
            var regex = /\/video\/([^\/?]+)/;
            var matches = url.match(regex);
            return matches[1];
        };

        var videoId = getVideoId(window.location.toString());

        // find a goal with exactly this exercise
        matchingGoal = goals.find(function(goal) {
            return _.find(goal.get('objectives'), function(ob) {
                return ob.type == "GoalObjectiveWatchVideo" &&
                    videoId == getVideoId(ob.url);
            });
        }) || null;

        if (matchingGoal === null) {
            // find an exercise process goal
            matchingGoal = goals.find(function(goal) {
                return _.find(goal.get('objectives'), function(ob) {
                    return ob.type == "GoalObjectiveAnyVideo";
                });
            }) || null;
        }

        return matchingGoal;
    },

    // find the most appriate goal to display for a given URL
    findMatchingGoalFor: function(url, goals) {
        var matchingGoal = null;

        if (window.location.pathname == "/exercises") {
            matchingGoal = this.findExerciseObjectiveFor(url, goals);
            if (matchingGoal !== null) {
                console.log('found a matching exercise goal');
            }
        }
        else if (window.location.pathname.indexOf("/video") === 0) {
            matchingGoal = this.findVideoObjectiveFor(url, goals);
            if (matchingGoal !== null) {
                console.log('found a matching video goal');
            }
        }

        // if we're not on a matching exercise or video page, just show the
        // most recently upated one
        if (matchingGoal === null) {
            matchingGoal = goals.at(0); // comparator is most recently updated
        }

        return matchingGoal;
    }
});

var GoalBookView = Backbone.View.extend({
    initialize: function() {
        $(this.el).delegate('.hide-goals', 'click', $.proxy(this.hide, this));
        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
    },
    show: function() {
        if (this.el.children.length === 0) {
            this.render();
        }
        return $(this.el).slideDown("fast");
    },
    hide: function() { return $(this.el).slideUp("fast"); },
    render: function() {
        console.log("rendered", this);
        var json = _.pluck(this.model.models, 'attributes');
        var goalsEl = $("#goalbook-tmpl").tmplPlugin({goals: json});
        $(this.el).html(goalsEl);
        return this;
    }
});

var GoalSummaryView = Backbone.View.extend({
    initialize: function(args) {
        $(this.el).delegate('#goals-drawer', 'click',
            $.proxy(args.goalBook.show, args.goalBook));

        this.model.bind('change', this.render, this);
        this.model.bind('reset', this.render, this);
    },
    render: function() {
        console.log("rendered", this);
        var goalsEl = $("#goals-tmpl").tmplPlugin(this.model.active().attributes);
        $(this.el).html(goalsEl);
        return this;
    }
});

$(function() {
    window.GoalBook = new GoalCollection(GoalsBootstrap);

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

// todo: make these real events?
var justWorkedOnGoal = function(goal) {
    console.log("Just worked on goal", goal);
};
var justWorkedOnObjective = function(newGoal, newObj) {
    console.log("Just worked on objective", newGoal, newObj);
};
var justFinishedGoal = function(goal) {
    console.log("Just finished goal", goal);
    showGoals();
    var recentlyCompleted = $('.recently-completed');
    var btnGoalHistory =$('#btn-goal-history');
    recentlyCompleted.children().each(
        function () {
            $(this).css('overflow', 'hidden').css('height', $(this).height());
    }).end()
    .delay(500)
    .animate({
        width: btnGoalHistory.width(),
        left: btnGoalHistory.position().left
    }).animate({
        top: btnGoalHistory.position().top - recentlyCompleted.position().top,
        height: '0',
        opacity: 'toggle'
    },
    'easeInOutCubic',
    function () {
        $(this).remove();
    }).end()
    .find('#btn-goal-history').animate({
        backgroundColor: 'orange'
    }).animate({
        backgroundColor: '#ddd'
    });
    //todo - also remove the goal from the model
};
var justFinishedObjective = function(newGoal, newObj) {
    console.log("Just finished objective", newObj);
    $("#goals-congrats").text('Just finished objective!').show().fadeOut(3000);
};

// assumes we already have Goals.all rendered. Incrementally updates what is
// already present, and fires some fake events
var incrementalUpdateGoals = function(updatedGoals) {
    _.each(updatedGoals, function(newGoal) {
        oldGoal = GoalBook.get(newGoal.id) || null;

        if (oldGoal !== null) {
            oldGoal.set(newGoal, {silent: true});
            oldGoal.calcDependents();
            oldGoal.change();
        }
        else {
            // todo: remove this, do something better
            console.log("Error: brand new goal appeared from somewhere");
        }
    });
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
        Throbber.hide();
        $("#popup-dialog").html('');
    },
    createSimpleGoal: function() {
        var selected_type = $("#goal-popup-dialog")
            .find("input[name=\"goal-type\"]:checked").val();
        var goal = predefinedGoalsList[selected_type];

        $('#create-simple-goal-error').html('');
        Throbber.show($("#create-simple-goal-button"), true);
        $.ajax({
            url: "/api/v1/user/goals/create",
            type: 'POST',
            dataType: 'json',
            data: $.param(goal),
            success: function(json) {
                Throbber.hide();
                createSimpleGoalDialog.hideDialog();

                Goals.all.push(json);
                updateGoals();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                Throbber.hide();
                $('#create-simple-goal-error').html('Goal creation failed');
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
