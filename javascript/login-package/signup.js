/**
 * Logic to handle the signup page (the page where a user may enter her e-mail
 * and get an e-mail to verify ownership of the address).
 */


/**
 * Entry point for initial signup page setup.
 */
Login.initSignupPage = function() {
    if (readCookie("u13")) {
        // User has the under-13 session cookie set - redirect.
        // This codepath will be most commonly hit if the user presses
        // the back button from the under-13 page.
        window.location.href = "/signup?under13=1";
        return;
    }

    $("#login-facebook").click(function(e) {
        Login.connectWithFacebook(
                "/postlogin?completesignup=1",
                true /* requireEmail */);
    });

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

    $("#email").focus().on("keypress", function(e) {
        if (e.keyCode === $.ui.keyCode.ENTER) {
            e.preventDefault();
            Login.submitSignup();
        }
    });

    $("#submit-button").click(function(e) {
        // Prevent direct form submission since we'll POST the data manually.
        e.preventDefault();
        Login.submitSignup();
    });
};

/**
 * Submits the signup attempt if it passes pre-checks.
 */
Login.submitSignup = function() {
    if (Login.submitDisabled_) {
        return;
    }

    // TODO(benkomalo): fix this at the bday-picker level.
    // "change" events aren't entirely reliable, and the bday-picker code
    // is prone to a bug where it doesn't properly update the hidden
    // field value in some cases on blur. Force a change prior to signup
    // so that the value is correct
    $("fieldset.birthday-picker").trigger("change");

    // Success!
    if (Login.ensureValid_("#email", "Email required")) {
        var data = $("#signup-form").serialize();
        $.ajax({
            "type": "POST",
            "url": $("#signup-form").prop("action"),
            "data": data,
            "dataType": "json",
            "success": function(data) {
                Login.handleSignupResponse(data);
            },
            "error": function() {
                // TODO(benkomalo): handle
            }
        });
    }
};


/**
 * Handles a response from the server for the signup attempt.
 */
Login.handleSignupResponse = function(data) {
    if (data["under13"]) {
        window.location.href = "/signup?under13=1";
        return;
    }

    var errors = data["errors"] || {};
    if (_.isEmpty(errors)) {
        // Success!
        var template = Templates.get("login.signup-success");
        var dialogEl = $(template({
                email: data["email"],
                resendDetected: data["resendDetected"],

                // On dev servers, the token is sent back down for easy
                // debugging. This is obviously not available on prod.
                token: data["token"]
            }))
            .appendTo($(document.body))
            .modal({
                backdrop: "static",
                show: true
            });
        Login.disableSubmit_();
    } else {
        // Only the e-mail can fail on a server side response from this
        // form.
        $("#error-text").text(errors["email"]);
    }
};

