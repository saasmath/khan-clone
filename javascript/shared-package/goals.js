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
    renderNavGoal();
    renderCurrentGoals();

    // event handlers
    $(".activate.simple-button").click(function(ev) {
        ev.preventDefault();
        var id = $(ev.target).closest(".goal").data('id')
        $.ajax({
            type: 'post',
            url: "/api/v1/user/goals/" + id + "/activate",
        });
        UIChangeActiveGoal(id);
    })
    $("#goals-drawer").toggle(showNavGoal, showCurrentGoals, showDrawer);
}
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
var renderNavGoal = function() {
    if (Goals.active) {
        var goalsEl = $("#goals-nav-tmpl").tmplPlugin(Goals.active);
        $('#goals-nav-container').html(goalsEl);
    }

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
