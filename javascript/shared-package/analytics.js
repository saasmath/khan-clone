// A set of internal analytics tools to get better analytics in Google Analytics.

(function() {
    var currentLinkTrackerTimeout = null;
    var pageLoadTime = null;
    
    window.Analytics = {

        // Utility to record event information on a user link click and report it 
        // to Google Analytics on the arrival page.
        //
        // To use this, just add the following markup to your link anchor tag:
        // <a href="/mypage" data-tag="Footer Link">Go to my page</a>
        LinkTracker: function() {
            window._gaq = window._gaq || [];

            // Get the page load timestamp (in milliseconds)
            pageLoadTime = (new Date()).getTime();

            // Detect an existing cookie, report it to GA and remove it
            var loadTag = readCookie("ka_event_tag");
            if (loadTag) {
                var duration = readCookie("ka_event_duration") * 1;
                _gaq.push(['_trackEvent', 'Page Load', 'Tag', loadTag, duration, true]);
                eraseCookie("ka_event_tag");
                eraseCookie("ka_event_duration");
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

                    currentLinkTrackerTimeout = setTimeout(function() {
                        _gaq.push(['_trackEvent', 'Page Nav', 'Tag', tag, timeDeltaSeconds, true]);
                        eraseCookie("ka_event_tag");
                        eraseCookie("ka_event_duration");
                    }, 1000);
                }
            });
        }

    };
})();

$(function() {
    // Initialize the LinkTracker automatically on page load.
    // This will set up the event handler and report an event
    // if the cookie has been set.
    Analytics.LinkTracker();
});

