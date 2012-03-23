/**
 * Out-of-the-box experience logic for the profile page.
 * Dependent on the contents of profile-package.
 */

if (typeof Profile !== "undefined") {
    Profile.showIntro_ = function() {
        if (Profile.profile.isPhantom()) {
            // For phantom users, don't show a tour flow, but a single dialog
            // with clear call-to-action to login.
            guiders.createGuider({
                buttons: [
                    {
                        action: guiders.ButtonAction.CLOSE,
                        text: "No thanks",
                        classString: "simple-button action-gradient"
                    },
                    {
                        action: guiders.ButtonAction.CLOSE,
                        text: "Cool. Let me login now!",
                        onclick: function() {
                            var postLoginUrl = "/postlogin?continue=" +
                                    encodeURIComponent(window.location.href);
                            window.location.href = "/login?continue=" +
                                    encodeURIComponent(postLoginUrl);
                        },
                        classString: "simple-button action-gradient green"
                    }
                ],
                title: "Log in to save and customize your profile!",
                description: "Your profile page shows you all the great progress you've made on Khan Academy. If you login, you can even customize and share your profile with your friends!",
                overlay: true
            }).show();
            return;
        }

        var isFullyEditable = Profile.profile.get("isDataCollectible");
        guiders.createGuider({
            id: "welcome",
            next: "basic-profile",

            buttons: [
                {
                    action: guiders.ButtonAction.CLOSE,
                    text: "No thanks. I know what I'm doing.",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "Cool. Show me around!",
                    classString: "simple-button action-gradient green"
                }
            ],
            title: "Welcome to your new profile!",
            description: "All of the stuff you liked is still here, and we've added some new things you can customize!",
            overlay: true
        }).show();

        guiders.createGuider({
            id: "basic-profile",
            next: "display-case",

            attachTo: ".basic-user-info",
            highlight: ".basic-user-info",
            overlay: true,
            position: 3,
            buttons: [
                {
                    action: guiders.ButtonAction.CLOSE,
                    text: "Close",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "Next",
                    classString: "simple-button action-gradient green"
                }
            ],
            title: "It's all about you.",
            description: isFullyEditable ?
                "This is your basic profile information, which you can now edit! You can change your name and pick a cool avatar just by clicking on it over there on the left." :
                "This is your basic profile information, which you can now customize with a cool avatar! Just click on it over there on the left."
        });

        guiders.createGuider({
            id: "display-case",
            next: "more-info",

            attachTo: ".display-case-cover",
            highlight: ".sticker-book",
            overlay: true,
            position: 6,
            buttons: [
                {
                    action: guiders.ButtonAction.CLOSE,
                    text: "Close",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "More! Show me more.",
                    classString: "simple-button action-gradient green"
                }
            ],
            title: "Show off your accomplishments.",
            description: "You can select up to five badges to show off in your very own shiny display case!"
        });

        guiders.createGuider({
            id: "more-info",
            next: "privacy-settings",

            attachTo: ".vertical-tab-list",
            highlight: ".vertical-tab-list",
            overlay: true,
            position: 3,
            buttons: (isFullyEditable ?
                [{
                    action: guiders.ButtonAction.CLOSE,
                    text: "Close",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "Next",
                    classString: "simple-button action-gradient green"
                }] : [{
                    action: guiders.ButtonAction.CLOSE,
                    text: "OK! Let me play with the page!",
                    classString: "simple-button action-gradient green"
                }]
            ),
            title: "Checking Your Vitals",
            description: "The statistics about your progress on Khan Academy are just a click away in the navigation menu. Don't worry, though, only you and your coaches can see this and nobody else."
        });

        if (isFullyEditable) {
            guiders.createGuider({
                id: "privacy-settings",

                attachTo: ".edit-visibility.visibility-toggler",
                highlight: ".user-info, .edit-visibility.visibility-toggler",
                overlay: true,
                position: 9,
                buttons: [{
                    action: guiders.ButtonAction.CLOSE,
                    text: "OK! Let me play with the page!",
                    classString: "simple-button action-gradient green"
                }],
                title: "Share With The World <span style='font-size:65%'>(but only if you want to)</span>",
                description: "The information in the box above can be made public. If you make your profile public, you'll get your own special space on Khan Academy. Other users will be able to visit your page. Don't worry! You can make your profile private at any time, in which case only you and your coaches can see your info."
            });
        }
    };
}
