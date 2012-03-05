
/**
 * Utilities for interacting with Facebook and its JS SDK.
 */
var FacebookUtil = {
    init: function() {
        if (!window.FB_APP_ID) return;

        window.fbAsyncInit = function() {
            FB.init({appId: FB_APP_ID, status: true, cookie: true, xfbml: true, oauth: true});

            if (!USERNAME) {
                FB.Event.subscribe("auth.login", function(response) {
                    // TODO(benkomalo): this login detection is too aggressive!
                    //     it means that the user will automatically auto-login
                    //     if they have authorized KA to access FB before.

                    if (response.authResponse) {
                        FacebookUtil.fixMissingCookie(response.authResponse);
                    }

                    var url = URL_CONTINUE || "/";
                    if (url.indexOf("?") > -1)
                        url += "&fb=1";
                    else
                        url += "?fb=1";

                    var hasCookie = !!readCookie("fbsr_" + FB_APP_ID);
                    url += "&hc=" + (hasCookie ? "1" : "0");

                    url += "&hs=" + (response.authResponse ? "1" : "0");

                    window.location = url;
               });
            }

            FB.getLoginStatus(function(response) {

                if (response.authResponse) {
                    FacebookUtil.fixMissingCookie(response.authResponse);
                }

                $("#page_logout").click(function(e) {

                    eraseCookie("fbsr_" + FB_APP_ID);

                    if (response.authResponse) {

                        FB.logout(function() {
                            window.location = $("#page_logout").attr("href");
                        });

                        e.preventDefault();
                        return false;
                    }

                });

            });
        };

        $(function() {
            var e = document.createElement("script"); e.async = true;
            e.src = document.location.protocol + "//connect.facebook.net/en_US/all.js";
            document.getElementById("fb-root").appendChild(e);
        });
    },

    fixMissingCookie: function(authResponse) {
        // In certain circumstances, Facebook's JS SDK fails to set their cookie
        // but still thinks users are logged in. To avoid continuous reloads, we
        // set the cookie manually. See http://forum.developers.facebook.net/viewtopic.php?id=67438.

        if (readCookie("fbsr_" + FB_APP_ID))
            return;

        if (authResponse && authResponse.signedRequest) {
            // Explicitly use a session cookie here for IE's sake.
            createCookie("fbsr_" + FB_APP_ID, authResponse.signedRequest);
        }
    }

};
FacebookUtil.init();

