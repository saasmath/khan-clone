// A set of utilities to track user interactions on the website (using MixPanel).
//
// Events can be either instantaneous or have a duration, and only one
// non-instantaneous event can be occurring at a time. If another event is begun,
// the previous event is ended automatically.
//
// The utility also attempts to resend events that happen just before the page is
// unloaded or on pages that are unloaded before the sending script is fully loaded.

(function() {

    var currentPage = null;
    var currentPageLoadTime = 0;
    var currentTrackingEvent = null;

    // Internal utility to make sure events get tracked even if the page is unloaded
    var analyticsStore = {
        persistData: {
            timestamp: 0,
            events: {}
        },

        // On page load, load the persist data from cookies and try to send any events
        // that didn't get sent last time.
        loadAndSendPersistData: function() {
            var persistData = $.parseJSON(readCookie("ka_analytics"));
            var currentTimeMS = (new Date()).getTime();
            var self = this;

            // Time out persist data after a minute
            if (persistData && (currentTimeMS - persistData.timestamp) < 60*1000) {
                this.persistData = persistData;

                _.each(persistData.events, function(event) {
                    mpq.track(event.name, event.parameters, function() {
                        self.clearEvent(event);
                    });
                });
            }
        },

        // Add an event to the queue to get sent to MixPanel
        addEvent: function(event) {
            var self = this;

            this.persistData.events[event.id] = event;
            self.storePersistData();

            // Send to tracker (may silently fail)
            mpq.track(event.name, event.parameters, function() {
                self.clearEvent(event);
            });
        },

        // Once an event is successfully sent, clear it from the queue
        clearEvent: function(event) {
            // If tracking succeeds, remove from persist data
            delete this.persistData.events[event.id];
            this.storePersistData();
            KAConsole.log("Successfully sent event " + event.name + " (" + event.id + ")");
        },

        // Save the queue to a cookie
        storePersistData: function() {
            this.persistData.timestamp = (new Date()).getTime();
            var persistDataJSON = JSON.stringify(this.persistData);

            createCookie("ka_analytics", persistDataJSON);
        }
    };

    window.Analytics = {

        // Called once on every page load (if MixPanel is enabled)
        trackInitialPageLoad: function(startTime) {
            var landingPage = (document.referrer.indexOf("khanacademy.org") > -1);

            analyticsStore.loadAndSendPersistData();

            // Send the final event before unloading the page
            $(window).unload(function() {
                Analytics._trackEventEnd((new Date()).getTime());
            });

            // Add event handler for decorated links
            $("body").on("click", "a", function(event) {
                var tag = $(this).attr("data-tag");
                if (tag) {
                    var href = $(this).attr("href");
                    Analytics.trackSingleEvent("Link Click", {
                        "Link Tag": tag,
                        "Href": href
                    });
                }
            });

            trackPageLoad(startTime, landingPage);
        },

        // Called once on arriving at a page (if MixPanel is enabled)
        // Differs from trackInitialPageLoad because using a Backbone Router
        // to navigate will trigger trackPageLoad.
        trackPageLoad: function(startTime, landingPage) {
            var currentTimeMS = (new Date()).getTime();
            var loadTimeMS = (startTime > 0) ? (currentTimeMS - startTime) : 0;

            analyticsStore.addEvent({
                id: "Page Load" + currentTimeMS,
                name: "Page Load",
                parameters: {
                    "Page": window.location.pathname,
                    "Load Time (ms)": loadTimeMS,
                    "Landing Page": (landingPage ? "Yes" : "No")
                }
            });

            currentPage = window.location.pathname;
            currentPageLoadTime = currentTimeMS;
            this.trackEventBegin("Page View", {});
        },

        handleRouterNavigation: function() {
            if (!currentPage) {
                return;
            }

            if (window.location.pathname !== currentPage) {
                Analytics.trackPageLoad(0, false);
            }
        },

        // Call this function in response to a user starting an interaction.
        // Returns the event object to use if you want to modify the parameters
        // or track the end of the event.
        trackEventBegin: function(eventName, parameters) {
            if (!currentPage) {
                return null;
            }

            var currentTimeMS = (new Date()).getTime();

            this._trackEventEnd(currentTimeMS);

            parameters._startTime = currentTimeMS;

            KAConsole.log("Started tracking event " + eventName + " (" + currentTimeMS + ")");

            currentTrackingEvent = {
                id: eventName + currentTimeMS,
                name: eventName,
                parameters: parameters
            };
            return currentTrackingEvent;
        },

        // Track the end of the event if it is the currently active event
        trackEventEnd: function(event) {
            if (event == currentTrackingEvent) {
                var currentTimeMS = (new Date()).getTime();
                this._trackEventEnd(currentTimeMS);

                // Go back to "Page View" mode because nothing else is active
                this.trackEventBegin("Page View", {});
            }
        },

        // Internal function to track the end of the current event
        _trackEventEnd: function(endTime) {
            if (currentTrackingEvent) {
                // Calculate event duration
                currentTrackingEvent.parameters["Page"] = currentPage;
                currentTrackingEvent.parameters["Event Time (ms)"] = endTime - currentTrackingEvent.parameters._startTime;
                currentTrackingEvent.parameters["Page Time (ms)"] = endTime - currentPageLoadTime;
                delete currentTrackingEvent.parameters._startTime;

                KAConsole.log("Stopped tracking event " + currentTrackingEvent.name + " after " + currentTrackingEvent.parameters["Event Time (ms)"] + " ms.");

                analyticsStore.addEvent(currentTrackingEvent);

                currentTrackingEvent = null;
            }
        },

        // Track an instantaneous event with no duration.
        trackSingleEvent: function(eventName, parameters) {
            if (!currentPage) {
                return null;
            }

            var currentTimeMS = (new Date()).getTime();

            parameters["Page"] = currentPage;
            parameters["Page Time (ms)"] = currentTimeMS - currentPageLoadTime;

            var event = {
                id: eventName + currentTimeMS,
                name: eventName,
                parameters: parameters
            };

            KAConsole.log("Tracking single event " + eventName + " (" + currentTimeMS + ")");

            analyticsStore.addEvent(event);
        }
    };
})();

