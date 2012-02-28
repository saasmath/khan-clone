/**
 * Various utilities related to the login or registration page.
 */

// Namespace
var Login = Login || {};

/**
 * Enumerated login "types" that the server recognizes to distinguish between
 * which type of credentials the user wishes to use to login.
 * Corresponds with values in login.py
 * @enum {string}
 */
Login.LoginType = {
    GOOGLE: 1,
    FACEBOOK: 2,
    PASSWORD: 3
};

/**
 * Entry point - usually called on DOMready.
 */
Login.init = function() {
    $("#login-google").click(function(e) {
        Login.connectWithGoogle();
    });
    $("#login-facebook").click(function(e) {
        $("#real_fb_button a").click();
    });

    if ($("#email").val()) {
        // Email filled in from previous attempt.
        $("#password").focus();
    } else {
        $("#email").focus();
    }

    $("#submit-button").click(function(e) {
        Login.loginWithPassword();
    });
};

/**
 * Kick off a login flow by using Google as an OAuth provider.
 */
Login.connectWithGoogle = function() {
    $("#type-input").val(Login.LoginType.GOOGLE);
    $("#login-form").submit();
};

/**
 * Login with a username and password.
 */
Login.loginWithPassword = function() {
    // Pre-validate.
    var valid = true;
    var identifier = $.trim($("#email").val());

    // Hide any previous failed login notification after any other attempt.
    $("#login-fail-message").hide();

    if (!identifier) {
        $("#email-error").text("Email or username required");
        valid = false;
    } else {
        $("#email-error").text("");
    }
    var password = $("#password").val();
    if (!password) {
        $("#password-error").text("Password required");
        valid = false;
    } else {
        $("#password-error").text("");
    }
    if (valid) {
        $("#type-input").val(Login.LoginType.PASSWORD);
        $("#login-form").submit();
    }
};

