/*
 * Views and logic for exercise/stack/card interactions
 */
var Exercises = {

    init: function(json) {
        // TODO(kamens) pass in some useful starting json
        // TODO(kamens) figure out the persistance model and hook 'er up via
        // backbone
        // this.userTopicModel = new UserTopicModel(json.somethingInteresting);

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
            "name": "addition_1",
            "incompleteStack": { cards: ["a", "b", "c"]},
            "completeStack": { cards: ["monkey"]},
        }));

    }

}
