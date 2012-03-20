/**
 * Logic to deal with with step 2 of the signup process, asking the user
 * for additional information like password and username (after
 * having verified her e-mail address already).
 */

/**
 * Initializes the form for completing the signup process
 */
Login.initCompleteSignupPage = function() {
    $("#nickname").focus();

    $("#password").on("keypress", function(e) {
        if (e.keyCode === $.ui.keyCode.ENTER) {
            Login.submitCompleteSignup();
        }
    });

    $("#submit-button").click(function() {
        Login.submitCompleteSignup();
    });
};


/**
 * Submits the complete signup attempt if it passes pre-checks.
 */
Login.submitCompleteSignup = function() {
    var valid = Login.ensureValid_("#nickname", "Name required");
    valid = Login.ensureValid_("#username", "Username required") && valid;
    valid = Login.ensureValid_("#password", "Password required") && valid;
    if (valid) {
        $("#registration-form").submit();
    }
};

