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
var renderGoals = function() {
    if (Goals.active) {
        var goal = Goals.active;
        var goalsEl = $("#goals-tmpl").tmplPlugin({
            title: goal.title,
            progress: totalProgress(goal.objectives).toFixed(0)
        });

        $("#goals-container").html(goalsEl);
    }
};
var updateGoals = function(data) {
    Goals.all = data;
    Goals.active = Goals.all[1];
    renderGoals();
    renderNavGoal();
};
var requestGoals = function() {
    $.ajax({ url: "/api/v1/user/goals", success: updateGoals });
};
var renderNavGoal = function() {
    if (Goals.active) {
        var goal = Goals.active;
        goal.progress = totalProgress(goal.objectives).toFixed(0);
        var goalsEl = $("#goals-nav-tmpl").tmplPlugin(goal);
        $('#goals-nav-container').html(goalsEl);
    }

    $("#goals-drawer").toggle(showNavGoal, hideNavGoal);

};
var showNavGoal = function() {
    $("#goals-nav-container").slideDown();
};
var hideNavGoal = function() {
    $("#goals-nav-container").slideUp();
};


$(function() { requestGoals() });
