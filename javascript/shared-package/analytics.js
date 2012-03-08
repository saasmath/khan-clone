/**
 * A set of utilities to track user interactions on the website (using MixPanel).
 *
 * Events can be either instantaneous or have a duration, and only one
 * non-instantaneous event can be occurring at a time. If another event is begun,
 * the previous event is ended automatically.
 *
 * The utility also attempts to resend events that happen just before the page is
 * unloaded or on pages that are unloaded before the sending script is fully loaded.
 */

(function() {

    var currentPage = null;
    var currentPageLoadTime = 0;
    var currentTrackingActivity = null;

    // Internal utility to make sure events get tracked even if the page is unloaded
    var analyticsStore = {
        persistData: {
            timestamp: 0,
            events: {}
        },

        // On page load, load the persist data from cookies and try to send any events
        // that didn't get sent last time.
        loadAndSendPersistData: function() {
            if (window.sessionStorage) {
                var persistData = null;
                try {
                    persistData = $.parseJSON(sessionStorage.getItem("ka_analytics"));
                } catch (e) { }

                var currentTimeMS = Date.now();

                // Time out persist data after a minute
                if (persistData && (currentTimeMS - persistData.timestamp) < 60 * 1000) {
                    var self = this;
                    this.persistData = persistData;

                    _.each(persistData.events, function(event) {
                        mpq.track(event.name, event.parameters, function() {
                            self.clearEvent(event);
                        });
                    });
                }
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
            if (window.sessionStorage) {
                this.persistData.timestamp = Date.now();
                var persistDataJSON = JSON.stringify(this.persistData);

                sessionStorage.setItem("ka_analytics", persistDataJSON);
            }
        }
    };

    window.Analytics = {

        // Called once on every page load (if MixPanel is enabled)
        trackInitialPageLoad: function(startTime) {
            var landingPage = (document.referrer.split('/')[2] === "www.khanacademy.org");

            analyticsStore.loadAndSendPersistData();

            // Send the final event before unloading the page
            $(window).unload(function() {
                Analytics._trackActivityEnd(Date.now());
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

            this.trackPageLoad(startTime, landingPage);
        },

        // Called once on arriving at a page (if MixPanel is enabled)
        // Differs from trackInitialPageLoad because using a Backbone Router
        // to navigate will trigger trackPageLoad.
        trackPageLoad: function(startTime, landingPage) {
            var currentTimeMS = Date.now();
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
            this.trackActivityBegin("Page View", {});
        },

        handleRouterNavigation: function(eventName) {
            if (eventName.indexOf("route:") != 0) {
                return;
            }
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
        trackActivityBegin: function(eventName, parameters) {
            if (!currentPage) {
                return null;
            }

            var currentTimeMS = Date.now();

            this._trackActivityEnd(currentTimeMS);

            parameters._startTime = currentTimeMS;

            KAConsole.log("Started tracking activity " + eventName + " (" + currentTimeMS + ")");

            currentTrackingActivity = {
                id: eventName + currentTimeMS,
                name: eventName,
                parameters: parameters
            };
            return currentTrackingActivity;
        },

        // Track the end of the event if it is the currently active event
        trackActivityEnd: function(event) {
            if (event == currentTrackingActivity) {
                var currentTimeMS = Date.now();
                this._trackActivityEnd(currentTimeMS);

                // Go back to "Page View" mode because nothing else is active
                this.trackActivityBegin("Page View", {});
            }
        },

        // Internal function to track the end of the current event
        _trackActivityEnd: function(endTime) {
            if (currentTrackingActivity) {
                // Calculate event duration
                currentTrackingActivity.parameters["Page"] = currentPage;
                currentTrackingActivity.parameters["Duration (ms)"] = endTime - currentTrackingActivity.parameters._startTime;
                currentTrackingActivity.parameters["Page Time (ms)"] = endTime - currentPageLoadTime;
                delete currentTrackingActivity.parameters._startTime;

                KAConsole.log("Stopped tracking activity " + currentTrackingActivity.name + " after " + currentTrackingActivity.parameters["Duration (ms)"] + " ms.");

                analyticsStore.addEvent(currentTrackingActivity);

                currentTrackingActivity = null;
            }
        },

        // Track an instantaneous event with no duration.
        trackSingleEvent: function(eventName, parameters) {
            if (!currentPage) {
                return null;
            }

            var currentTimeMS = Date.now();

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

