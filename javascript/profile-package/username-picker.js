/**
 * Code to handle the username picker.
 */

UsernamePickerView = Backbone.View.extend({
    className: "username-picker",

    events: {
        "keyup #username": "onUsernameKeyup_",
        "click #claim-username": "onClaimUsernameClick_"
    },

    initialize: function() {
        this.template = Templates.get("profile.username-picker");
        this.keyupTimeout = null;
        this.model.bind("validate:username",
            _.bind(this.showMessage_, this));
    },

    render: function() {
        var context = {username: this.model.get("username")},
            html = this.template(context);
        $(this.el).html(html);
        return this;
    },

    onUsernameKeyup_: function(e) {
        if (e.keyCode === 13) {
            // Pressing enter does not save. Should it?
            this.onTimeout_();
            return;
        }

        this.$(".sidenote").text("typing");
        if (this.keyupTimeout) {
            clearTimeout(this.keyupTimeout);
        }
        this.keyupTimeout = setTimeout(_.bind(this.onTimeout_, this), 1000);
    },

    onTimeout_: function() {
        this.$(".sidenote").text("validating");
        this.model.validateUsername(this.$("#username").val());
        this.keyupTimeout = null;
    },

    showMessage_: function(isValid, message) {
        this.$("#claim-username").prop("disabled", !isValid);
        this.$(".sidenote").text(message);
    },

    onChangeSuccess_: function(model, response) {
        this.showMessage_(true, "saved.");
    },

    onChangeError_: function(model, response) {
        this.showMessage_(false, response.responseText);
    },

    onClaimUsernameClick_: function() {
        var username = this.$("#username").val(),
            attrs = {
                username: username
            },
            options = {
                success: _.bind(this.onChangeSuccess_, this),
                error: _.bind(this.onChangeError_, this)
            };

        this.model.save(attrs, options);
    }
});
