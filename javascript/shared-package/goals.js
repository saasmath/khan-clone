var totalProgress = function(objectives) {
    var progress = 0;
    if (objectives.length) {
        var count = 0;
        $.each(objectives, function(i, ob) {
            progress += ob.progress;
        });
        progress = progress/objectives.length;
    }
    return progress;
};

_.mixin({
    // like groupBy, but assumes there is a unique key for each element.
    indexBy: function(seq, key) {
        return _.reduce(seq, function(m, el){ m[el[key]] = el; return m;}, {});
    }
});

// anotate goal with progress counts and overall progress
var annotateGoal = function(goal) {
    goal.progress = totalProgress(goal.objectives);
    goal.progressStr = (goal.progress * 100).toFixed(0);
    goal.objectiveProgress = _.filter(goal.objectives, function(obj) {
        return obj.progress >= 1;
    }).length;
};

var saveGoals = function(newGoals) {
    if (newGoals) {
        Goals.all = newGoals;
    } else {
        console.log("warning, goals were updated without saveGoals, events lost!");
    }
    _.each(Goals.all, annotateGoal);
};

// todo: surely this is in a library somewhere?
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

var findExerciseObjectiveFor = function(url) {
    var matchingGoal = null;

    var exid = parseQueryString(url).exid;
    // find a goal with exactly this exercise
    $.each(Goals.all, function(i, goal) {
        var objective = $.grep(goal.objectives, function(ob) {
            return ob.type == "GoalObjectiveExerciseProficiency" &&
                exid == parseQueryString(ob.url).exid;
        });
        if (objective.length > 0) {
            matchingGoal = goal;
            return false;
        }
    });

    if (matchingGoal === null) {
        // find an exercise process goal
        $.each(Goals.all, function(i, goal) {
            var objective = $.grep(goal.objectives, function(ob) {
                return ob.type == "GoalObjectiveAnyExerciseProficiency";
            });
            if (objective.length > 0) {
                matchingGoal = goal;
                return false;
            }
        });
    }

    return matchingGoal;
};

var findVideoObjectiveFor = function(url) {
    var matchingGoal = null;

    var getVideoId = function(url) {
        var regex = /\/video\/([^\/?]+)/;
        var matches = url.match(regex);
        return matches[1];
    };

    var videoId = getVideoId(window.location.toString());

    // find a goal with exactly this exercise
    $.each(Goals.all, function(i, goal) {
        var objective = $.grep(goal.objectives, function(ob) {
            return ob.type == "GoalObjectiveWatchVideo" &&
                videoId == getVideoId(ob.url);
        });
        if (objective.length > 0) {
            matchingGoal = goal;
            return false;
        }
    });

    if (matchingGoal === null) {
        // find an exercise process goal
        $.each(Goals.all, function(i, goal) {
            var objective = $.grep(goal.objectives, function(ob) {
                return ob.type == "GoalObjectiveAnyVideo";
            });
            if (objective.length > 0) {
                matchingGoal = goal;
                return false;
            }
        });
    }

    return matchingGoal;
};

// find the most appriate goal to display for a given URL
var findMatchingGoalFor = function(url) {
    var matchingGoal = null;

    if (window.location.pathname == "/exercises") {
        matchingGoal = findExerciseObjectiveFor(url);
        if (matchingGoal !== null) {
            console.log('found a matching exercise goal');
        }
    }
    else if (window.location.pathname.indexOf("/video") === 0) {
        matchingGoal = findVideoObjectiveFor(url);
        if (matchingGoal !== null) {
            console.log('found a matching video goal');
        }
    }
    // if we're not on a matching exercise or video page, just show the most recent goal
    if (matchingGoal === null) {
        matchingGoal = mostRecentlyUpdatedGoal(Goals.all);
    }

    return matchingGoal;
};

var mostRecentlyUpdatedGoal = function(goals) {
    if (goals.length > 0) {
        var matchingGoal = goals[0];
        var minDate = new Date(matchingGoal.updated);

        $.each(Goals.all, function(i, goal) {
            var currentDate = new Date(goal.updated);
            if (currentDate > minDate) {
                matchingGoal = goal;
                minDate = currentDate;
            }
        });

        return matchingGoal;
    }
    return null;
};

var displayGoals = function() {
    if (Goals.all.length) {
        _.each(Goals.all, function(g) { g.active = false;});

        Goals.active = findMatchingGoalFor(window.location.toString());
        Goals.active.active = true;

        renderAllGoalsUI();
    }
};

var renderAllGoalsUI = function() {
    renderGoalSummaryArea();
    renderGoalbook();

    $("#goals-container").delegate("#goals-drawer", "click", showGoals);
    $("#goals-nav-container").delegate(".hide-goals", "click", hideGoals);
};
var renderGoalSummaryArea = function(goal) {
    goal = goal || Goals.active;
    if (goal) {
        var goalsEl = $("#goals-tmpl").tmplPlugin(goal);
        $("#goals-container").html(goalsEl);
    } else {
        $("#goals-container").html('');
    }
};
var renderGoalbook = function() {
    if (Goals.all.length) {
        var goalsEl = $("#goalbook-tmpl").tmplPlugin({goals: Goals.all});
        $("#goals-nav-container").html(goalsEl);
    } else {
        $("#goals-nav-container").html('');
    }
};
var showGoals = function() {
    $("#goals-nav-container").slideDown('fast');
};
var hideGoals = function() {
    $("#goals-nav-container").slideUp('fast');
};


var requestGoals = function() {
    $.ajax({ url: "/api/v1/user/goals/current", success: updateGoals });
};
var updateGoals = function(goals) {
    saveGoals(goals);
    displayGoals();
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
    $("#goals-congrats").text('Just finished goal!').show().fadeOut(3000);
};
var justFinishedObjective = function(newGoal, newObj) {
    console.log("Just finished objective", newObj);
    $("#goals-congrats").text('Just finished objective!').show().fadeOut(3000);
};
// assumes we already have Goals.all rendered. Incrementally updates what is
// already present, and fires some fake events
var incrementalUpdateGoals = function(updatedGoals) {
    _.each(updatedGoals, function(newGoal) {
        annotateGoal(newGoal);
        oldGoal = _.find(Goals.all, function(g) { return g.id === newGoal.id; });

        if (typeof oldGoal !== 'undefined') {
            // rerender all linked views
            if ( Goals.active.id === newGoal.id ) {
                // this goal was the active goal, update the summary area
                renderGoalSummaryArea(newGoal);
            }
            // update goal in goalbook
            var newRow = $("#goalrow-tmpl").tmplPlugin(newGoal);
            $(".all-goals .goal[data-id="+newGoal.id+"]").replaceWith(newRow);

            // inspect old element to see what changed, fire events
            justWorkedOnGoal(newGoal);
            // check for goal completion
            if (newGoal.progress !== oldGoal.progress) {
                // check to see if we just finished the goal
                if (newGoal.progress >= 1) {
                    justFinishedGoal(newGoal);
                }
                else {
                    // now look for updated objectives
                    _.each(newGoal.objectives, function(newObj, i) {
                        var oldObj = oldGoal.objectives[i];
                        if (newObj.progress > oldObj.progress) {
                            justWorkedOnObjective(newGoal, newObj);
                            if (newObj.progress >= 1) {
                                justFinishedObjective(newGoal, newObj);
                            }
                        }
                    });
                }
            }

            // overwrite old goal with new goal
            _.extend(oldGoal, newGoal);
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

$(function() {
    if (typeof(Goals) === "undefined") {
        Goals = {
            all: [],
            active: null
        };
    }
    _.each(Goals.all, annotateGoal);
    displayGoals();
});
