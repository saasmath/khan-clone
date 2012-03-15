HoverCardView = Backbone.View.extend({

    initialize: function() {
        this.template = Templates.get("shared.hover-card");
    },

    render: function() {
        var json = this.model.toJSON();
        // TODO: this data isn't specific to any profile and is more about the library.
        // It should probably be moved out eventially.

        //TODO(marcia): Use real counts
        json["countExercises"] = 300;
        json["countVideos"] = 3000;
        $(this.el).html(this.template(json)).find("abbr.timeago").timeago();

        return this;
    }
});
