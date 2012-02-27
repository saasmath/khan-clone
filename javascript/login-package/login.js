/**
 * Various utilities related to the login or registration page.
 */

// Namespace
var Login = Login || {};

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
};

/**
 * Kick off a login flow by using Google as an OAuth provider.
 */
Login.connectWithGoogle = function() {
    $("#login-form").submit();
};
