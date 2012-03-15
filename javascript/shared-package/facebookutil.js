
/**
 * Utilities for interacting with Facebook and its JS SDK.
 */
var FacebookUtil = {

    init: function() {
        if (!window.FB_APP_ID) return;

        window.fbAsyncInit = function() {
            FB.init({
                appId: FB_APP_ID,
                status: false, // Fetch status conditionally below.
                cookie: true,
                xfbml: true,
                oauth: true
            });

            if (FacebookUtil.isUsingFbLogin()) {
                // Only retrieve the status if the user has opted to login
                // with Facebook
                FB.getLoginStatus(function(response) {
                    if (response.authResponse) {
                        FacebookUtil.fixMissingCookie(response.authResponse);
                    } else {
                        // The user is no longer signed into Facebook - must
                        // have logged out of FB in another window or disconnected
                        // the service in their FB settings page.
                        eraseCookie("fbl");
                    }
                });
            }

            $("#page_logout").click(function(e) {
                var hostname = window.location.hostname;

                // By convention, dev servers lead with "local." in the address
                // even though the domain registered with FB is without it.
                if (hostname.indexOf("local.") === 0) {
                    hostname = hostname.substring(6);
                }

                // The Facebook cookies are set on ".www.khanacademy.org",
                // though older ones are not. Clear both to be safe.
                eraseCookie("fbsr_" + FB_APP_ID);
                eraseCookie("fbsr_" + FB_APP_ID, "." + hostname);
                eraseCookie("fbm_" + FB_APP_ID);
                eraseCookie("fbm_" + FB_APP_ID, "." + hostname);
                eraseCookie("fbl");

                if (FacebookUtil.isUsingFbLogin()) {
                    // If the user used FB to login, log them out of FB, too.
                    try {
                        FB.logout(function() {
                            window.location = $("#page_logout").attr("href");
                        });
                        e.preventDefault();
                        return false;
                    } catch (e) {
                        // FB.logout can throw if the user isn't actually
                        // signed into FB. We can get into this state
                        // in a few odd ways (if they re-sign in using Google,
                        // then sign out of FB in a separate tab).
                        // Just ignore it, and have logout work as normal.
                    }
                }
            });
        };

        $(function() {
            var e = document.createElement("script"); e.async = true;
            e.src = document.location.protocol + "//connect.facebook.net/en_US/all.js";
            document.getElementById("fb-root").appendChild(e);
        });
    },

    isUsingFbLoginCached_: undefined,

    /**
     * Whether or not the user has opted to sign in to Khan Academy
     * using Facebook.
     */
    isUsingFbLogin: function() {
        if (FacebookUtil.isUsingFbLoginCached_ === undefined) {
            FacebookUtil.isUsingFbLoginCached_ = readCookie("fbl") || false;
        }
        return FacebookUtil.isUsingFbLoginCached_;
    },

    /**
     * Indicates that the user has opted to sign in to Khan Academy
     * using Facebook.
     */
    markUsingFbLogin: function() {
        // Generously give 30 days to the fbl cookie, which indicates
        // that the user is using FB to login.
        createCookie("fbl", true, 30);
    },

    fixMissingCookie: function(authResponse) {
        // In certain circumstances, Facebook's JS SDK fails to set their cookie
        // but still thinks users are logged in. To avoid continuous reloads, we
        // set the cookie manually. See http://forum.developers.facebook.net/viewtopic.php?id=67438.

        if (readCookie("fbsr_" + FB_APP_ID)) {
            return;
        }

        if (authResponse && authResponse.signedRequest) {
            // Explicitly use a session cookie here for IE's sake.
            createCookie("fbsr_" + FB_APP_ID, authResponse.signedRequest);
        }
    }
};
FacebookUtil.init();

