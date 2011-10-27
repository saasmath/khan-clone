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
var updateGoals = function(data) {
    Goals.all = data;
    $.each(Goals.all, function(i, goal) {
        goal.progress = totalProgress(goal.objectives).toFixed(0);
    });
    Goals.active = Goals.all[1];

    renderGoals();
    renderNavGoal();
    renderCurrentGoals();
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
var renderNavGoal = function() {
    if (Goals.active) {
        var goalsEl = $("#goals-nav-tmpl").tmplPlugin(Goals.active);
        $('#goals-nav-container').html(goalsEl);
    }
    $("#goals-drawer").toggle(showNavGoal, showCurrentGoals, showDrawer);
};
var renderCurrentGoals = function() {
    if (Goals.all.length) {
        var goalsEl = $("#goals-all-tmpl").tmplPlugin({goals: Goals.all});
        $("#goals-current-container").html(goalsEl);
    }
};

var showNavGoal = function() {
    $("#goals-nav-container").slideDown();
    $("#goals-current-container").slideUp();
};
var showCurrentGoals = function() {
    $("#goals-nav-container").slideUp();
    $("#goals-current-container").slideDown();
};
var showDrawer = function() {
    $("#goals-nav-container").slideUp();
    $("#goals-current-container").slideUp();
}

$(function() { requestGoals() });
