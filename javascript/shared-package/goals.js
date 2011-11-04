var totalProgress = function(objectives) {
    var progress = 0;
    if (objectives.length) {
        var count = 0;
        $.each(objectives, function(i, ob) {
            progress += ob.progress;
        });
        progress = progress/objectives.length;
    }
    return progress * 100;
};
var renderAllGoalsUI = function() {
    renderGoals();
    renderCurrentGoals();

    $("#goals-drawer").click(showGoals);
    $(".hide-goals").click(hideGoals);
};
var saveGoals = function(data) {
    if (data) {
        Goals.all = data;
    }

    // anotate goals with progress counts and overall progress
    $.each(Goals.all, function(i, goal) {
        goal.progress = totalProgress(goal.objectives).toFixed(0);
        goal.objectiveProgress = 0;

        $.each(goal.objectives, function(i, ob) {
            if (ob.progress >= 1) {
                goal.objectiveProgress += 1;
            }
        });
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
};

var displayGoals = function() {
    if (Goals.all.length) {
        Goals.active = findMatchingGoalFor(window.location.toString());
        renderAllGoalsUI();
    }
};
var requestGoals = function(callback) {
    $.ajax({ url: "/api/v1/user/goals/current", success: callback || saveGoals });
};
var renderGoals = function() {
    if (Goals.active) {
        var goalsEl = $("#goals-tmpl").tmplPlugin(Goals.active);
        $("#goals-container").html(goalsEl);
    }
};
var renderCurrentGoals = function() {
    if (Goals.all.length) {
        var goalsEl = $("#goalbook-tmpl").tmplPlugin({goals: Goals.all});
        $("#goals-nav-container").html(goalsEl).draggable({
            handle: ".drag-handle"
        });
    }
};

var showGoals = function() {
    $("#goals-nav-container").show();
};
var hideGoals = function() {
    $("#goals-nav-container").hide();
};

var updateGoals = function(data) {
    saveGoals(data);
    displayGoals();
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
    if ( typeof Goals !== 'undefined' && Goals.all ) {
        updateGoals();
    }
});
