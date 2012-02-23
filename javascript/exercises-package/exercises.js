/**
 * Views and logic for exercise/stack/card interactions
 * TODO(kamens): don't love the name "Exercises" for this namespace
 */
var Exercises = {

    exercise: null,
    userTopic: null,
    currentCard: null,
    incompleteStack: null,
    completeStack: null,

    /**
     * Called to initialize the exercise page. Passed in with JSON information
     * rendered from the server. See templates/exercises/power_template.html for details.
     */
    init: function(json) {

        this.exercise = json.exercise;

        // TODO(kamens): figure out the persistance model and hook 'er up
        // this.userTopicModel = new UserTopicModel(json.userTopic);
        this.userTopic = json.userTopic;

        $(Khan).bind("newProblem", function() { Exercises.nextCard(); });
        $(Khan).bind("stackComplete", function() { Exercises.endOfStack(); });

        Exercises.render();
    },

    render: function() {

        var profileExercise = Templates.get("exercises.exercise");

        Handlebars.registerPartial("exercise-header", Templates.get("exercises.exercise-header"));

        $(".exercises-content-container").html(profileExercise({
            // TODO(kamens): Useful dict data here like crazzzyyyyyyyy
            exercise: this.exercise,
            userTopic: this.userTopic,
        }));

        this.incompleteStack = new Exercises.Stack({
            model: this.userTopic.incompleteStack,
            el: $(".incomplete-stack")
        }); 

        this.completeStack = new Exercises.Stack({
            model: this.userTopic.completeStack,
            el: $(".complete-stack")
        }); 

        this.currentCard = new Exercises.CurrentCard({ el: $(".current-card") });
        this.currentCard.render();

    },

    nextCard: function() {

        if (this.currentCard.model) {
            this.completeStack.pushCurrent();
        }

        this.incompleteStack.popToCurrent();

        // TODO(kamens): this rendering pattern probably isn't gonna work for
        // required pretty animations
        this.incompleteStack.render();
        this.completeStack.render();

    },

    endOfStack: function() {

        // TODO(kamens): something else.
        KAConsole.debugEnabled = true;
        KAConsole.log("Ended the stack!");

    }

};

/**
 * View of a stack of cards
 */
Exercises.Stack = Backbone.View.extend({

    template: Templates.get("exercises.stack"),

    render: function() {
        this.el.html(this.template(this.model));
        return this;
    },

    /**
     * Pop next card off of Stack and hook it up to the CurrentCard model
     */
    popToCurrent: function() {

        Exercises.currentCard.model = _.head(this.model.cards);
        this.model.cards = _.tail(this.model.cards);

        if (!this.model.cards.length) {
            $(Khan).trigger("stackComplete");
        }

    },

    /**
     * Push CurrentCard model to Stack
     */
    pushCurrent: function() {
        this.model.cards.push(Exercises.currentCard.model);
    }

});

/**
 * View of the single, currently-visible card
 */
Exercises.CurrentCard = Backbone.View.extend({

    template: Templates.get("exercises.current-card"),

    render: function(ix) {

        Handlebars.registerPartial("problem-template", Templates.get("exercises.problem-template"));
        this.el.html(this.template(this.model));

        return this;

    }

});
