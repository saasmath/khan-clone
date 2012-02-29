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
Login.initLoginPage = function() {
    $("#login-google").click(function(e) {
        Login.connectWithGoogle();
    });
    $("#login-facebook").click(function(e) {
        $("#real_fb_button a").click();
    });

    if ($("#identifier").val()) {
        // Email/username filled in from previous attempt.
        $("#password").focus();
    } else {
        $("#identifier").focus();
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
    var identifier = $.trim($("#identifier").val());

    // Hide any previous failed login notification after any other attempt.
    $("#login-fail-message").hide();

    if (!identifier) {
        $("#identifier-error").text("Email or username required");
        valid = false;
    } else {
        $("#identifier-error").text("");
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

/**
 * Entry point for registration page setup.
 */
Login.initRegistrationPage = function() {
    $("#birthday-picker").birthdaypicker({
        placeholder: false,
        classes: "simple-input ui-corner-all login-input",

        // Jan 1, 13 years ago
        defaultDate: new Date(new Date().getFullYear() - 13, 0, 1)
    });

    $("#nickname").focus();
};

