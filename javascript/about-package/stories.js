
var Stories = Stories || {};

Stories.render = function(story_data) {

    $.each(story_data.content, function(ix, story) {

        var view = new Stories.SmallView({ model: story });
        $(story_data.target).append(view.render().el);

    });

};

Stories.show = function(elStory, model) {

    $(".content-teaser-show, .content-teaser-hide")
        .removeClass("content-teaser-show")
        .removeClass("content-teaser-hide");
    
    setTimeout(function() {

        $(elStory).addClass("content-teaser-show");

        setTimeout(function() {

            $(elStory).addClass("content-teaser-hide");

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
                    });

        }, 400);

    }
    , 1);

};

Stories.SmallView = Backbone.View.extend({

    template: Templates.get( "about.story" ),

    render: function() {
        var model = this.model;

        $(this.el)
            .html(this.template(this.model))
            .find(".story")
                .click(function() { Stories.show(this, model); });

        return this;
    }

});

Stories.FullView = Backbone.View.extend({

    template: Templates.get( "about.story-full" ),

    render: function() {
        $(this.el)
            .html(this.template(this.model));
        return this;
    }

});
