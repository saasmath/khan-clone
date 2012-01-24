/**
 * Out-of-the-box experience logic for the profile page.
 * Dependent on the contents of profile-package.
 */

if (typeof Profile !== "undefined") {
    guiders.createGuider({
        buttons: [{name: "Close"}],
        title: "Welcome!",
        description: "This is your new profile page!",
        overlay: true
    }).show();
}
