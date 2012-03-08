
/**
 * Utilities for user settings, such as changing a password.
 */
var Settings = {

    template: Templates.get("profile.settings"),

    render: function(targetJel) {
        targetJel.html(this.template());

        $("#password1").on(
                Keys.textChangeEvents,
                Keys.wrapTextChangeHandler(this.onPasswordInput_, this));
        $("#password2").on(
                Keys.textChangeEvents,
                Keys.wrapTextChangeHandler(this.onPasswordInput_, this));

        $("#submit-settings").click(_.bind(this.onClickSubmit_, this));
    },

    onPasswordInput_: function(e) {
        if (e.target.id === "password1" || e.target.id === "password2") {
            this.validateNewPassword();
        }
    },

    onClickSubmit_: function(e) {
        console.log("submit!");
        // TODO(benkomalo): handle.
    },

    // Must be consistent with what's on the server in auth/passwords.py
    MIN_PASSWORD_LENGTH: 8,

    validateNewPassword: _.debounce(function() {
        var password1 = $("#password1").val();
        var password2 = $("#password2").val();

        // Check basic length.
        if (password1 && password1.length < Settings.MIN_PASSWORD_LENGTH) {
            $(".sidenote.password1")
                    .addClass("error")
                    .text("Password too short");
        } else {
            $(".sidenote.password1").removeClass("error").text("");
        }

        // Check matching.
        if (password2 && password2 != password1) {
            $(".sidenote.password2").addClass("error").text("Passwords don't match.");
        } else {
            $(".sidenote.password2").removeClass("error").text("");
        }
    }, 500)
};
