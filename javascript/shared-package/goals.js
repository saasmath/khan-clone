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

$(function() { requestGoals(); });
