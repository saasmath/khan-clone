
var Stories = Stories || {};

Stories.router = null;
Stories.views = {};
Stories.cShown = 0;

Stories.render = function(story_data) {

    var row = null;
    var lastStory = null;
    var storiesPerRow = 3;

    $.each(story_data.content, function(ix, story) {

        if (ix % storiesPerRow == 0) {
            row = $("<div class='row'></div>");
            $(story_data.target).append(row);
        }

        if (lastStory) {
            lastStory.next_story = story;
            story.prev_story = lastStory;
        }

        var view = new Stories.SmallView({ model: story });
        row.append($(view.render(ix).el));

        Stories.views[story.name] = view;
        lastStory = story;

    });

    Stories.router = new Stories.StoryRouter();
    Backbone.history.start({
        pushState: true,
        root: "/stories"
    });

};

Stories.SmallView = Backbone.View.extend({

    template: Templates.get( "stories.story" ),

    render: function(ix) {
        var model = this.model;

        $(this.el)
            .html(this.template(this.model))
            .addClass("span-one-third")
            .addClass("story-container")
            .find(".story")
                .addClass(this.randomRotation())
                .addClass(this.randomEnvelope())
                .click(function() { Stories.navigateTo(model); });

        return this;
    },

    randomRotation: function() {
        return this.randomChoice(["rotate-5", "rotate-neg-7", "rotate-neg-3"]);
    },

    randomEnvelope: function() {
        return this.randomChoice(["envelope-1", "envelope-2", "envelope-3", "envelope-4"]);
    },

    randomChoice: function(choices) {
        // Consistent style for this particular story
        Math.seedrandom(this.model.name);

        var index = Math.floor(Math.random() * (choices.length - 1));
        return choices[index];
    },

    showFull: function() {

        $(".content-teaser-show, .content-teaser-hide")
            .removeClass("content-teaser-show")
            .removeClass("content-teaser-hide");

        var model = this.model;
        var jelStory = $(this.el).find(".story");

        setTimeout(function() {

            $(jelStory).addClass("content-teaser-show");

            setTimeout(function() {

                $(jelStory).addClass("content-teaser-hide");
                var jelOld = $("#modal-story");

                var view = new Stories.FullView({ model: model });

                // If modal was previously visible, remove 'fade' class
                // so transition swaps immediately
                var classToRemove = Stories.cShown > 0 ? "fade" : "";

                $(view.render().el)
                    .find("#modal-story")
                        .removeClass(Stories.cShown > 0 ? "fade" : "")
                        .appendTo(document.body)
                        .bind("show", function() { Stories.cShown++; })
                        .bind("hidden", function() {

                            $(this).remove();

                            $(jelStory)
                                .removeClass("content-teaser-show")
                                .removeClass("content-teaser-hide");

                            // If no other modal dialog is on its way
                            // to becoming visible, push history
                            Stories.cShown--;
                            if (!Stories.cShown) {
                                Stories.navigateTo(null);
                            }
                        })
                        .modal({
                            keyboard: true,
                            backdrop: true,
                            show: true
                        });

                // Hide any existing modal dialog
                jelOld.removeClass("fade").modal("hide");

            }, 400);

        }
        , 1);

    },

});

Stories.FullView = Backbone.View.extend({

    template: Templates.get( "stories.story-full" ),

    render: function() {
        var model = this.model;

        $(this.el)
            .html(this.template(this.model))
           .find(".prev-btn")
                .not(".disabled")
                    .click(function() { Stories.navigateTo(model.prev_story); })
                    .end()
                .end()
            .find(".next-btn")
                .not(".disabled")
                    .click(function() { Stories.navigateTo(model.next_story); });
        return this;
    }

});

Stories.navigateTo = function(model) {
    if (model) {
        Stories.router.navigate("/" + model.name, true);
    }
    else {
        Stories.router.navigate("");
    }
};

Stories.StoryRouter = Backbone.Router.extend({

    routes: {
        "": "showNone",
        "/:story": "showStory"
    },

    showNone: function() {
        // If #modal-story is still in the DOM,
        // we got here via history navigation and
        // need to remove it.
        $("#modal-story").modal("hide");
    },

    showStory: function(name) {
        var view = Stories.views[name];
        if (view) {
            view.showFull();
        }
    }

});
