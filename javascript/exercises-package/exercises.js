/**
 * Views and logic for exercise/stack/card interactions
 * TODO(kamens): don't love the name "Exercises" for this namespace
 */
var Exercises = {

    exercise: null,
    userTopic: null,

    currentCard: null,
    currentCardView: null,

    incompleteStackCollection: null,
    incompleteStackView: null,

    completeStackCollection: null,
    completeStackView: null,

    /**
     * Called to initialize the exercise page. Passed in with JSON information
     * rendered from the server. See templates/exercises/power_template.html for details.
     */
    init: function(json) {

        this.exercise = json.exercise;

        // TODO(kamens): figure out the persistance model and hook 'er up
        // this.userTopicModel = new UserTopicModel(json.userTopic);
        this.userTopic = json.userTopic;

        this.incompleteStack = new Exercises.StackCollection(this.userTopic.incompleteStack); 
        this.completeStack = new Exercises.StackCollection(this.userTopic.completeStack); 

        Exercises.render();

        this.listenForEvents();
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

        this.incompleteStackView = new Exercises.StackView({
            collection: this.incompleteStack,
            el: $(".incomplete-stack")
        }); 

        this.completeStackView = new Exercises.StackView({
            collection: this.completeStack,
            el: $(".complete-stack")
        }); 

        this.currentCardView = new Exercises.CurrentCardView({
            el: $(".current-card") }
        );

        this.currentCardView.render();
        this.incompleteStackView.render();
        this.completeStackView.render();

    },

    listenForEvents: function() {

        $(Khan).bind("newProblem", function() { Exercises.nextCard(); });

        this.completeStack.bind("add", function() { Exercises.completeStackView.animateToHead(); });

        this.incompleteStack
            .bind("remove", function() { Exercises.incompleteStackView.animateToCurrent(); })
            .bind("stackComplete", function() { Exercises.endOfStack(); });

    },

    nextCard: function() {

        if (this.currentCard) {

            // Pop off of incomplete and move current to complete
            this.incompleteStack.pop();
            this.completeStack.add(this.currentCard);
            this.currentCard = null;

        }

        if (!this.currentCard && this.incompleteStack.length === 0) {
            this.incompleteStack.trigger("stackComplete");
        }
        else {
            this.currentCard = this.incompleteStack.peek();
        }

    },

    endOfStack: function() {

        // TODO(kamens): something else.
        KAConsole.debugEnabled = true;
        KAConsole.log("Ended the stack!");

    }

};

/**
 * Collection model of a stack of cards
 */
Exercises.StackCollection = Backbone.Collection.extend({

    model: Exercises.Card,

    peek: function() {
        return _.head(this.models);
    },

    pop: function() {
        this.remove(this.peek());
    }

});

/**
 * View of a stack of cards
 */
Exercises.StackView = Backbone.View.extend({

    template: Templates.get("exercises.stack"),

    render: function() {
        this.el.html(this.template({cards: this.collection}));
        return this;
    },

    /**
     * Animate popping card off of stack and moving it to current card slot
     */
    animateToCurrent: function() {

        this.el
            .find(".card-container")
                .first()
                    .addClass("flipped")
                    .delay(600)
                    .slideUp(
                        function() { $(this).remove(); }
                    );

    },

    /**
     * Animate pushing current card slot onto head of stack
     */
    animateToHead: function() {

        this.el
            .find(".stack")
                .prepend(
                    $(Templates.get("exercises.card")())
                        .css("display", "none")
                )
                .find(".card-container")
                    .first()
                        .slideDown();

    }

});

/**
 * Model of any (current or in-stack) card
 */
Exercises.Card = Backbone.Model.extend({});

/**
 * View of the single, currently-visible card
 */
Exercises.CurrentCardView = Backbone.View.extend({

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
