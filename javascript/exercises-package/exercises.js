/*
 * Views and logic for exercise/stack/card interactions
 */
var Exercises = {

    exercise: null,
    userTopic: null,

    /**
     * Called to initialize the exercise page. Passed in with JSON information
     * rendered from the server. See templates/exercises/power_template.html for details.
     */
    init: function(json) {

        this.exercise = json.exercise;

        // TODO(kamens) figure out the persistance model and hook 'er up
        // this.userTopicModel = new UserTopicModel(json.userTopic);
        this.userTopic = json.userTopic;

        Exercises.render();
    },

    render: function() {

        var profileExercise = Templates.get("exercises.exercise");

        Handlebars.registerPartial("exercise-header", Templates.get("exercises.exercise-header"));

        Handlebars.registerHelper("renderStack", function(stack) {
            var currentStackContext = _.extend({}, this, { stack: stack });
            return Templates.get("exercises.stack")(currentStackContext);
        });

        $(".exercises-content-container").html(profileExercise({
            // TODO(kamens): Useful dict data here like crazzzyyyyyyyy
            exercise: this.exercise,
            userTopic: this.userTopic,
        }));

    }

}
