/**
 * Various utilities related to the login page.
 */

// TODO(benkomalo): do more on-the-fly client side validation of things like
// valid usernames or passwords

// Namespace
var Login = Login || {};

/**
 * Initializes the host login page. Note that most of the username/password
 * fields of the login page are hosted in an iframe so it can be sent
 * over https. Google/FB logins are in the outer container.
 */
Login.initLoginPage = function(options) {
    $("#login-facebook").click(function(e) {
        Login.connectWithFacebook(
            options["continueUrl"], true /* requireEmail */);
    });
};


/**
 * A base URL that represents the post login URL after a login.
 * This is needed by inner iframes that may be hosted on https
 * domains and need to forward the user to a normal http URL
 * after a successful login.
 */
Login.basePostLoginUrl;

/**
 * Initializes the inner contents (within the iframe) of the login
 * form.
 */
Login.initLoginForm = function(options) {
    Login.basePostLoginUrl = options["basePostLoginUrl"] || "";

    if ($("#identifier").val()) {
        // Email/username filled in from previous attempt.
        $("#password").focus();
    } else {
        $("#identifier").focus();
    }

    $("#submit-button").click(function(e) {
        e.preventDefault();
        Login.loginWithPassword();
    });
    $("#password").on("keypress", function(e) {
        if (e.keyCode === $.ui.keyCode.ENTER) {
            e.preventDefault();
            Login.loginWithPassword();
        }
    });
};

/**
 * Use Facebook's JS SDK to connect with Facebook.
 * @param {string} continueUrl The URL to redirect to after a successful login.
 * @param {boolean} requireEmail An optional parameter to indicate whether or
 *     not the user needs to grant extended permissions to our app so we
 *     can retrieve their e-mail address.
 */
Login.connectWithFacebook = function(continueUrl, requireEmail) {
    FacebookUtil.runOnFbReady(function() {
        // TODO(benkomalo): add some visual indicator that we're trying.
        var extendedPerms = requireEmail ? {"scope": "email"} : undefined;
        FB.login(function(response) {
            if (response) {
                FacebookUtil.fixMissingCookie(response);
            }

            if (response["status"] === "connected") {
                FacebookUtil.markUsingFbLogin();
                var url = continueUrl || "/";
                if (url.indexOf("?") > -1) {
                    url += "&fb=1";
                } else {
                    url += "?fb=1";
                }

                window.location = url;
            } else {
                // TODO(benkomalo): handle - the user didn't login properly in facebook.
            }
       }, extendedPerms);
    });
};

/**
 * Login with a username and password.
 */
Login.loginWithPassword = function() {
    // Hide any previous failed login notification after any other attempt.
    // Use "visibility" so as to avoid any jerks in the layout.
    $("#error-text").css("visiblity", "hidden");

    // Pre-validate.
    if (Login.ensureValid_("#identifier", "Email or username required") &&
            Login.ensureValid_("#password", "Password required")) {
        Login.asyncFormPost(
                $("#login-form"),
                function(data) {
                    // Server responded with 200, but login may have failed.
                    if (data["errors"]) {
                        Login.onPasswordLoginFail(data["errors"]);
                    } else {
                        Login.onPasswordLoginSuccess(data);
                        // Don't re-enable the login button as we're about
                        // to refresh the page.
                    }
                },
                function(data) {
                    // Hard failure - server is inaccessible or having issues
                    // TODO(benkomalo): handle
                });
    }
};

Login.submitDisabled_ = false;
Login.navigatingAway_ = false;

/**
 * Disables form submit on a login attempt, to prevent duplicate tries.
 */
Login.disableSubmit_ = function() {
    $("#submit-button").attr("disabled", true);
    Login.submitDisabled_ = true;
};

/**
 * Restores form submission ability, usually after a response from a server
 * from a login/signup attempt.
 */
Login.enableSubmit_ = function() {
    $("#submit-button").removeAttr("disabled");
    Login.submitDisabled_ = false;
};

/**
 * Handle a failed attempt at logging in with a username/password.
 */
Login.onPasswordLoginFail = function(errors) {
    var text;
    if (errors["badlogin"]) {
        text = "Your login or password is incorrect.";
    } else {
        // Unexpected error. This shouldn't really happen but
        // just in case...
        text = "Error logging in. Please try again.";
    }

    $("#error-text").text(text).css("visibility", "");
    $("#password").focus();
};

/**
 * Handle a successful login response, which includes auth data.
 * This will cause the page to fully reload to a /postlogin URL
 * generated by the server containing the new auth token which will be
 * set as a cookie.
 */
Login.onPasswordLoginSuccess = function(data) {
    var auth = data["auth"];
    var continueUri = data["continue"] || "/";
    window.top.location.replace(
            Login.basePostLoginUrl +
            "postlogin?continue=" + encodeURIComponent(continueUri) +
            "&auth=" + encodeURIComponent(auth));

    Login.navigatingAway_ = true;
};

/**
 * Validates a field in a login/signup form and displays an error on failure
 * on $("error-text").
 * If validation fails, the field will automatically be focused.
 */
Login.ensureValid_ = function(
        selector, errorText, checkFunc) {
    // By default - check that it's not just empty whitespace.
    checkFunc = checkFunc || function() {
        var value = $(selector).val();
        return !!$.trim(value);
    };
    if (!checkFunc()) {
        $("#error-text").text(errorText);
        $(selector).focus();
        return false;
    }

    // Include whitespace so that empty/non-empty values don't affect layout.
    $("#error-text").html("&nbsp;");
    return true;
};

/**
 * Submits a form in the background via a hidden iframe.
 * Only one form may be in flight at a time, since only a single iframe
 * is used.
 *
 * This is useful so that the page doesn't have to navigate away and we can
 * handle errors more gracefully.
 *
 * Note that this is quite crude and makes no guarantees about history
 * state (on most browsers, each request will likely create a history entry).
 */
Login.asyncFormPost = function(jelForm, success, error) {
    if (Login.submitDisabled_) {
        return;
    }

    Login.disableSubmit_();
    $.ajax({
        "type": "POST",
        "url": jelForm.prop("src"),
        "data": jelForm.serialize(),
        "dataType": "json",
        "success": success,
        "error": error,
        "complete": function() {
            if (!Login.navigatingAway_) {
                Login.enableSubmit_();
            }
        }
    });
};
