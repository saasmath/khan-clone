/**
 * Out-of-the-box experience logic for the profile page.
 * Dependent on the contents of profile-package.
 */

if (typeof Profile !== "undefined") {
    // Some of the items highlighted in the intro flow are rendered on
    // the client. Asynchronously start the intro flow so that those
    // items can be rendered first.
    window.setTimeout(function() {
        guiders.createGuider({
            id: "welcome",
            next: "basic-profile",

            buttons: [{
                action: guiders.ButtonAction.NEXT,
                text: "Cool. Show me around!"
            }],
            title: "Welcome!",
            description: "Welcome to your new profile page. We added some stuff here which will help you track your own progress and share a bit of it with the world.",
            overlay: true
        }).show();

        guiders.createGuider({
            id: "basic-profile",
            next: "display-case",

            attachTo: ".basic-user-info",
            highlight: ".basic-user-info",
            overlay: true,
            position: 3,
            buttons: [{
                action: guiders.ButtonAction.NEXT,
                text: "Next"
            }],
            title: "Khan Academy, now with more You!",
            description: "This is your basic profile information, which you can now edit to your own liking! You can change your nickname and one of many hip avatars just by clicking on it over there on the left"
        });

        guiders.createGuider({
            id: "display-case",
            next: "more-info",

            attachTo: ".display-case-cover",
            highlight: ".sticker-book",
            overlay: true,
            position: 6,
            buttons: [{
                action: guiders.ButtonAction.NEXT,
                text: "More! Show me more!"
            }],
            title: "Show Off In Style",
            description: "You can even select up to five badges to show off in your own shiny display case of achievements!"
        });

        guiders.createGuider({
            id: "more-info",
            next: "privacy-settings",

            attachTo: ".vertical-tab-list",
            highlight: ".vertical-tab-list",
            overlay: true,
            position: 3,
            buttons: [{
                action: guiders.ButtonAction.NEXT,
                text: "Next"
            }],
            title: "Checking Your Vitals",
            description: "The statistics about your progress on Khan Academy can still be accessed by just a click here in the navigation menu. Don't worry, though, only you and your coaches can see this and nobody else."
        });

        guiders.createGuider({
            id: "privacy-settings",

            attachTo: ".edit-visibility",
            highlight: ".user-info, .edit-visibility",
            overlay: true,
            position: 9,
            buttons: [{
                action: guiders.ButtonAction.CLOSE,
                text: "OK! Let me play with the page!"
            }],
            title: "Share With The World <span style='font-size:65%'>(but only if you want to)</span>",
            description: "The information in the box above can be made public. You'll get your own special space on Khan Academy where people can go to visit your page, but only if you enable it with this toggle. You can make your profile private at any time, in which case only you and your coaches can see your info"
        });

    }, 0);
}
