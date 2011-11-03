var Goals = {
    all: [],
    active: null
};
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

    // event handlers
    $(".activate.simple-button").click(function(ev) {
        ev.preventDefault();
        var id = $(ev.target).data('goal-id');
        $.ajax({
            type: 'post',
            url: "/api/v1/user/goals/" + id + "/activate"
        });
        UIChangeActiveGoal(id);
    });
    $("#goals-drawer").click(showGoals);
    $(".hide-goals").click(hideGoals);
};
var UIChangeActiveGoal = function(id) {
    $.each(Goals.all, function(i, goal) {
        if (goal.id == id) {
            Goals.active = goal;
            goal.active = true;
        }
        else {
            goal.active = false;
        }
    });
    renderAllGoalsUI();
};
var updateGoals = function(data) {
    Goals.all = data;
    $.each(Goals.all, function(i, goal) {
        goal.progress = totalProgress(goal.objectives).toFixed(0);
        goal.objectiveProgress = 0;

        $.each(goal.objectives, function(i, ob) {
            if (ob.progress >= 1) {
                goal.objectiveProgress += 1;
            }
        });

        if (goal.active) {
            Goals.active = goal;
        }
    });
    renderAllGoalsUI();
};
var requestGoals = function() {
    $.ajax({ url: "/api/v1/user/goals", success: updateGoals });
};
var renderGoals = function() {
    if (Goals.active) {
        var goalsEl = $("#goals-tmpl").tmplPlugin(Goals.active);
        $("#goals-container").html(goalsEl);
    }
};
var renderCurrentGoals = function() {
    if (Goals.all.length) {
        var goalsEl = $("#goals-all-tmpl").tmplPlugin({goals: Goals.all});
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

var predefinedGoalsList = {
    "five_exercises" : {
        "title": "Complete Five Exercises",
        "objective1_type": "GoalObjectiveAnyExerciseProficiency",
        "objective2_type": "GoalObjectiveAnyExerciseProficiency",
        "objective3_type": "GoalObjectiveAnyExerciseProficiency",
        "objective4_type": "GoalObjectiveAnyExerciseProficiency",
        "objective5_type": "GoalObjectiveAnyExerciseProficiency",
    },
    "five_videos" : {
        "title": "Watch Five Videos",
        "objective1_type": "GoalObjectiveAnyVideo",
        "objective2_type": "GoalObjectiveAnyVideo",
        "objective3_type": "GoalObjectiveAnyVideo",
        "objective4_type": "GoalObjectiveAnyVideo",
        "objective5_type": "GoalObjectiveAnyVideo",
    },
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
        var selected_type = $("#goal-popup-dialog").find("input[name=\"goal-type\"]:checked").val();
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
                updateGoals(Goals.all);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                Throbber.hide();
                $('#create-simple-goal-error').html('Goal creation failed');
            },
        });
    },
};

$(function() { requestGoals(); });
