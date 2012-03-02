// A set of internal analytics tools to get better analytics in Google Analytics.

(function() {
    var currentLinkTrackerTimeout = null;
    var pageLoadTime = null;
    var mpqEnabled = false;
    
    window.Analytics = {

        // Utility to record event information on a user link click and report it 
        // to Google Analytics on the arrival page.
        //
        // To use this, just add the following markup to your link anchor tag:
        // <a href="/mypage" data-tag="Footer Link">Go to my page</a>
        LinkTracker: function(params) {
            window._gaq = window._gaq || [];

            // Get the page load timestamp (in milliseconds)
            pageLoadTime = (new Date()).getTime();

            mpqEnabled = params.mpqEnabled || false;

            // Detect an existing cookie, report it to GA and remove it
            var loadTag = readCookie("ka_event_tag");

            if (loadTag) {
                var duration = readCookie("ka_event_duration") * 1;
                var referrer = readCookie("ka_event_referrer");
                _gaq.push(['_trackEvent', 'Page Load', loadTag, referrer, duration, true]);
                if (mpqEnabled) {
                    mpq.track("Page Load", {
                        "Path": window.location.pathname,
                        "Link tag": loadTag,
                        "Previous page time": duration
                    });
                }

                eraseCookie("ka_event_tag");
                eraseCookie("ka_event_duration");
                eraseCookie("ka_event_referrer");
            } else {
                if (mpqEnabled) {
                    mpq.track("Page Load", {
                        "Path": window.location.pathname
                    });
                }
            }

            // Set an event handler to listen for clicks on anchor tags with a data-tag attribute
            $("body").on("click", "a", function(event) {
                var tag = $(this).attr("data-tag");
                if (tag) {
                    if (currentLinkTrackerTimeout) {
                        clearTimeout(currentLinkTrackerTimeout);
                    }

                    var timeDelta = ((new Date()).getTime() - pageLoadTime);
                    var timeDeltaSeconds = Math.floor(timeDelta/1000);
                    createCookie("ka_event_tag", tag);
                    createCookie("ka_event_duration", timeDeltaSeconds);
                    createCookie("ka_event_referrer", window.location.pathname);

                    currentLinkTrackerTimeout = setTimeout(function() {
                        _gaq.push(['_trackEvent', 'Page Nav', tag, window.location.pathname, timeDeltaSeconds, true]);
                        if (mpqEnabled) {
                            mpq.track("Page Navigate", {
                                "Path": window.location.pathname,
                                "Link tag": tag,
                                "Previous page time": timeDeltaSeconds
                            });
                        }

                        // Reset page load time
                        pageLoadTime = (new Date()).getTime();

                        eraseCookie("ka_event_tag");
                        eraseCookie("ka_event_duration");
                        eraseCookie("ka_event_referrer");
                    }, 1000);
                }
            });
        }

    };
})();

