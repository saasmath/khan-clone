
var Stories = Stories || {};

Stories.router = null;
Stories.views = {};

Stories.render = function(story_data) {

    var row = null;
    var storiesPerRow = 3;

    $.each(story_data.content, function(ix, story) {

        if (ix % storiesPerRow == 0) {
            row = $("<div class='row'></div>");
            $(story_data.target).append(row);
        }

        var view = new Stories.SmallView({ model: story });
        row.append($(view.render(ix).el));

        Stories.views[story.name] = view;

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
                .addClass(ix % 3 == 0 || ix == 2 ? "envelope-1" : "envelope-2")
                .click(function() { Stories.router.navigate("/" + model.name, true); });

        return this;
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
                            $(".content-teaser-hide")
                                .removeClass("content-teaser-show")
                                .removeClass("content-teaser-hide");

                            Stories.router.navigate("");
                        });

            }, 400);

        }
        , 1);

    }

});

Stories.FullView = Backbone.View.extend({

    template: Templates.get( "stories.story-full" ),

    render: function() {
        $(this.el)
            .html(this.template(this.model));
        return this;
    }

});

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
