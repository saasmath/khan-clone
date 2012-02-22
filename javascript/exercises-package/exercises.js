/*
 * Views and logic for exercise/stack/card interactions
 */
var Exercises = {

    init: function(json) {
        // TODO(kamens) pass in some useful starting json
        // this.incomingStack = new StackModel(json.somethingInteresting);
        // this.outgoingStack = new StackModel(json.somethingInteresting);

        Exercises.render();
    },

    render: function() {

        var profileExercise = Templates.get("exercises.exercise");

        // TODO(kamens) partials and helpers here like crazzzzyyyyy

        $(".exercises-content-container").html(profileExercise({
            // TODO(kamens): Useful dict data here like crazzzyyyyyyyy
        }));

    }

}
