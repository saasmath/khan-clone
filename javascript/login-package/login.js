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
    $("#email").focus();
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
    $("#type-input").val(Login.LoginType.PASSWORD);
    $("#login-form").submit();
};

