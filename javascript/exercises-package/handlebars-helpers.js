Handlebars.registerPartial("exercise-header", Templates.get("exercises.exercise-header"));
Handlebars.registerPartial("small-exercise-icon", Templates.get("exercises.small-exercise-icon"));
Handlebars.registerPartial("card", Templates.get("exercises.card"));
Handlebars.registerPartial("card-leaves", Templates.get("exercises.card-leaves"));

/**
 * Render an exercise skill-bar with specified ending position and optional
 * starting position, exercise states, and whether or not proficiency was just
 * earned and should be animated.
 */
Handlebars.registerHelper("skill-bar", function(end, start, exerciseStates, justEarnedProficiency) {

    var template = Templates.get("exercises.skill-bar"),
        context = _.extend({
                start: start || 0,
                end: end || 0,
                justEarnedProficiency: !!(justEarnedProficiency)
            }, 
            exerciseStates);
    
    return template(context);

}); 
