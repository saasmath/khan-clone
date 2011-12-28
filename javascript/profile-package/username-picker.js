/**
 * Code to handle the username picker.
 */

UsernamePickerModel = Backbone.Model.extend({
    defaults: {
        "username": ""
    },

    url: "/api/v1/user/username"
});

UsernamePickerView = Backbone.View.extend({
    className: "username-picker",

    events: {
        "change #username": "onUsernameChanged_"
    },

    initialize: function() {
        this.template = Templates.get("profile.username-picker");
    },

    render: function() {
        $(this.el).html(this.template(this.model.toJSON()));
        return this;
    },

    onChangeSuccess_: function(model, response) {
        this.showMessage_("Yay", "success");
    },

    onChangeError_: function(model, response) {
        this.showMessage_(response.responseText, "error");
    },

    showMessage_: function(message, className) {
        $("#message-bar").html(message)
            .addClass(className)
            .fadeIn()
            .delay(1000)
            .fadeOut("fast", function() {
                $(this).removeClass(className);
            });
    },

    onUsernameChanged_: function(e) {
        // TODO: validate
        var value = this.$("#username").val(),
            that = this,
            attrs = {
                username: value
            },
            options = {
                success: _.bind(this.onChangeSuccess_, this),
                error: _.bind(this.onChangeError_, this)
            };

        this.model.save(attrs, options);
    }
});
