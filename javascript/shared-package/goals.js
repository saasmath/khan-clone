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

var saveGoals = function(newGoals) {
    var oldGoals = null;
    if (newGoals) {
        oldGoals = Goals.all;
        Goals.all = newGoals;
    } else {
        console.log("warning, goals were updated without saveGoals, events lost!");
    }

    // anotate goals with progress counts and overall progress
    _.each(Goals.all, function(goal) {
        goal.progress = totalProgress(goal.objectives);
        goal.progressStr = (goal.progress * 100).toFixed(0);
        goal.objectiveProgress = _.filter(goal.objectives, function(obj) {
            return obj.progress >= 1;
        }).length;
    });

    return oldGoals;
};

var detectEvents = function(oldGoals) {
    // now look for recently completed goals or objectives
    var goalsByIdNew = _.indexBy(Goals.all, 'id');
    var goalsById = _.indexBy(oldGoals, 'id');

    _.each(goalsById, function(g) { g.isUpdated = false; });

    _.each(goalsByIdNew, function(newGoal) {
        oldGoal = goalsById[newGoal.id];
        if (typeof oldGoal !== 'undefined') {
            if (newGoal.progress !== oldGoal.progress) {
                // check to see if we just finished the goal
                if (newGoal.progress >= 1) {
                    console.log("Just finished goal!", newGoal);
                    alert("Yay, you just finished a goal! Insert feelgood effect here.");
                    $("#goals-drawer").effect('highlight');
                }
                else {
                    // now look for updated objectives
                    _.each(newGoal.objectives, function(newObj, i) {
                        var oldObj = oldGoal.objectives[i];
                        if (newObj.progress !== oldObj.progress) {
                            console.log("Just worked on", newGoal, newObj);
                            if (newObj.progress >= 1) {
                                console.log("Just finished objective", newObj);
                                $("#goals-drawer").effect('highlight');
                            }
                        }
                    });
                }
            }
        }
        else {
            console.log("Found a brand new goal!", newGoal);
        }
        oldGoal.isUpdated = true;
    });

    _(goalsById).chain()
        .filter(function(g) { return g.isUpdated === false; })
        .each(function(goal) {
            console.log("This goal has no update and will disappear!", goal);
        });
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
        Goals.active = findMatchingGoalFor(window.location.toString());
        renderAllGoalsUI();
    }
};

var renderAllGoalsUI = function() {
    renderGoalSummaryArea();
    renderGoalbook();

    $("#goals-drawer").click(showGoals);
    $(".hide-goals").click(hideGoals);
};
var showGoals = function() {
    $("#goals-nav-container").slideDown('fast');
};
var hideGoals = function() {
    $("#goals-nav-container").slideUp('fast');
};

var renderGoalSummaryArea = function() {
    if (Goals.active) {
        var goalsEl = $("#goals-tmpl").tmplPlugin(Goals.active);
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


var requestGoals = function(callback) {
    $.ajax({ url: "/api/v1/user/goals/current", success: updateGoals });
};
var updateGoals = function(goals) {
    var oldGoals = saveGoals(goals);
    displayGoals();
    if (oldGoals) {
       detectEvents(oldGoals);
    }
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
        var Goals = {
            all: [],
            active: null
        };
    }
    updateGoals();
});
