
var Stories = Stories || {};

Stories.router = null;
Stories.views = {};

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
                .addClass(ix % 2 == 0 ? "rotate-5" : (ix % 3 == 0 ? "rotate-neg-7" : "rotate-neg-7"))
                .addClass("envelope-" + ((ix % 3) + 1))
                .click(function() { Stories.navigateTo(model); });

        return this;
    },

    showFull: function() {

        $(".content-teaser-show, .content-teaser-hide")
            .removeClass("content-teaser-show")
            .removeClass("content-teaser-hide");

        var model = this.model;
        var jelStory = $(this.el).find(".story");
        var wasVisible = $("#modal-story").is(":visible");

        setTimeout(function() {

            $(jelStory).addClass("content-teaser-show");

            setTimeout(function() {

                $(jelStory).addClass("content-teaser-hide");

                $("#modal-story").modal("hide");

                var view = new Stories.FullView({ model: model });

                $(view.render().el)
                    .find("#modal-story")
                        .appendTo(document.body)
                        .modal({
                            keyboard: true,
                            backdrop: true,
                            show: true
                        })
                        .bind("hidden", function() {
                            $(this).remove();

                            var isVisible = $("#modal-story").is(":visible");
                            if (!wasVisible && !isVisible) {
                                $(".content-teaser-hide")
                                    .removeClass("content-teaser-show")
                                    .removeClass("content-teaser-hide");

                                Stories.navigateTo(null);
                            }
                        });

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
