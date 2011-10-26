var Goals = [];
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
    if (Goals.length) {
        var goal = Goals[0];
        var goalsEl = $("#goals-tmpl").tmplPlugin({
            title: goal.title,
            progress: totalProgress(goal.objectives).toFixed(0)
        });

        $("#goals-container").html(goalsEl);
    }
};
var updateGoals = function(data) {
    Goals = data;
    renderGoals();
};
var requestGoals = function() {
    $.ajax({ url: "/api/v1/user/goals", success: updateGoals });
};

$(function() { requestGoals() });
