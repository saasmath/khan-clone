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

        Handlebars.registerPartial("exercise-header", Templates.get("exercises.exercise-header"));
        Handlebars.registerPartial("card", Templates.get("exercises.card"));
        Handlebars.registerPartial("problem-template", Templates.get("exercises.problem-template"));

        var profileExercise = Templates.get("exercises.exercise");

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
        this.incompleteStack.render();
        this.completeStack.render();

    },

    nextCard: function() {

        if (this.currentCard.model) {
            this.completeStack.pushCurrent();
        }

        this.incompleteStack.popToCurrent();

        if (this.currentCard.empty() && this.incompleteStack.empty()) {
            $(Khan).trigger("stackComplete");
        }

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

    empty: function() {
        return this.model.cards.length === 0;
    },

    render: function() {
        this.el.html(this.template(this.model));
        return this;
    },

    /**
     * Pop next card off of Stack, hook it up to the CurrentCard model,
     * and animate the transition.
     */
    popToCurrent: function() {

        Exercises.currentCard.model = _.head(this.model.cards);
        this.model.cards = _.tail(this.model.cards);

        this.el
            .find(".card_container")
                .first()
                    .addClass("flipped")
                    .delay(600)
                    .slideUp(
                        function() { $(this).remove(); }
                    );

    },

    /**
     * Push CurrentCard model to Stack
     */
    pushCurrent: function() {
        this.model.cards.push(Exercises.currentCard.model);

        this.el
            .find(".stack")
                .prepend(
                    $(Templates.get("exercises.card")())
                        .css("display", "none")
                        .addClass("flipped")
                )
                .find(".card_container")
                    .first()
                        .slideDown(function() {
                            $(this).removeClass("flipped");
                        });
    }

});

/**
 * View of the single, currently-visible card
 */
Exercises.CurrentCard = Backbone.View.extend({

    template: Templates.get("exercises.current-card"),
    model: null,

    empty: function() {
        return !this.model;
    },

    render: function(ix) {
        this.el.html(this.template(this.model));
        return this;
    }

});
