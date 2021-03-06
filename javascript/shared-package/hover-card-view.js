HoverCardView = Backbone.View.extend({

    initialize: function() {
        this.template = Templates.get("shared.hover-card");
    },

    render: function() {
        var json = {};

        if (this.model) {
            json = this.model.toJSON();
            if (this.model.isInaccessible()) {
                json["isInaccessible"] = this.model.isInaccessible();
                json["messageOnly"] = true;
            }
        } else {
            json["messageOnly"] = true;
        }

        $(this.el).html(this.template(json)).find("abbr.timeago").timeago();

        return this;
    }
});
