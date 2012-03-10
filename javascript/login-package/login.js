/**
 * Various utilities related to the login or registration page.
 */

// TODO(benkomalo): do more on-the-fly client side validation of things like
// valid usernames or passwords

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
        Login.connectWithFacebook();
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
    $("#password").on("keypress", function(e) {
        if (e.keyCode === $.ui.keyCode.ENTER) {
            Login.loginWithPassword();
        }
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
 * Use Facebook's JS SDK to connect with Facebook.
 */
Login.connectWithFacebook = function() {
    FB.login(function(response) {
        if (response) {
            FacebookUtil.fixMissingCookie(response);
        }

        if (response["status"] === "connected") {
            FacebookUtil.markUsingFbLogin();
            var url = URL_CONTINUE || "/";
            if (url.indexOf("?") > -1) {
                url += "&fb=1";
            } else {
                url += "?fb=1";
            }

            var hasCookie = !!readCookie("fbsr_" + FB_APP_ID);
            url += "&hc=" + (hasCookie ? "1" : "0");
            url += "&hs=" + (response ? "1" : "0");

            window.location = url;
        } else {
            // TODO(benkomalo): handle - the user didn't login properly in facebook.
        }
   });
};

/**
 * Login with a username and password.
 */
Login.loginWithPassword = function() {

    // Hide any previous failed login notification after any other attempt.
    $("#login-fail-message").hide();

    // Pre-validate.
    var valid = Login.ensureValid_("#identifier", "Email or username required");
    valid = Login.ensureValid_("#password", "Password required") && valid;

    if (valid) {
        $("#type-input").val(Login.LoginType.PASSWORD);
        $("#login-form").submit();
    }
};

/**
 * Validates a field in the login form and displays an error on failure.
 */
Login.ensureValid_ = function(selector, errorText, checkFunc) {
    // By default - check that it's not just empty whitespace.
    checkFunc = checkFunc || function() {
        var value = $(selector).val();
        return !!$.trim(value);
    };
    if (!checkFunc()) {
        $(selector + "-error").text(errorText);
        return false;
    }

    $(selector + "-error").text("");
    return true;
};

/**
 * Entry point for registration page setup.
 */
Login.initRegistrationPage = function() {
    var dateData = $("#birthday-picker").data("date");
    var defaultDate;
    if (dateData) {
        var parts = dateData.split("-");
        if (parts.length === 3) {
            var year = parseInt(parts[0], 10);
            var month = parseInt(parts[1], 10) - 1;
            var date = parseInt(parts[2], 10);
            if (!isNaN(year + month + date)) {
                defaultDate = new Date(year, month, date);
            }
        }
    }
    if (!defaultDate) {
        // Jan 1, 13 years ago
        defaultDate = new Date(new Date().getFullYear() - 13, 0, 1);
    }

    $("#birthday-picker").birthdaypicker({
        placeholder: false,
        classes: "simple-input ui-corner-all login-input",
        defaultDate: defaultDate
    });

    $("#nickname").focus();

    $("#submit-button").click(function() {
        Login.submitRegistration();
    });
    $("#password").on("keypress", function(e) {
        if (e.keyCode === $.ui.keyCode.ENTER) {
            Login.submitRegistration();
        }
    });
};

/**
 * Submits the registration attempt if passes pre-checks.
 */
Login.submitRegistration = function() {
    var valid = Login.ensureValid_("#nickname", "Name required");
    valid = Login.ensureValid_("#username", "Username required") && valid;
    valid = Login.ensureValid_("#email", "Email required") && valid;
    valid = Login.ensureValid_("#password", "Password required") && valid;

    // Success!
    if (valid) {
        $("#registration-form").submit();
    }
};

