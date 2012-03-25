
// TODO: would be nice if this were part of a larger KnowledgeMap context
// instead of needing the KnowledgeMap naming prefix.

/*
 * All models that may be represented on the knowledge map
 */
var KnowledgeMapModels = {

    Topic: Backbone.Model.extend({

        initialize: function(attributes) {

            // Translate topic properties to standard node properties
            this.set({
                name: this.get("id"),
                h_position: this.get("x"),
                v_position: this.get("y"),
                display_name: this.get("standalone_title"),
                lowercaseName: this.get("standalone_title").toLowerCase(),
                zoomBounds: [KnowledgeMapGlobals.options.minZoom, KnowledgeMapGlobals.options.minZoom],
            });

            return Backbone.Model.prototype.initialize.call(this, attributes);

        },

        url: function() {
            return "/topicexercise/" + this.get("id");
        },

    }),

    Exercise: Backbone.Model.extend({
        initialize: function(attributes) {

            // TODO(kamens): remove/replace w/ simple streak bar/icon?
            if (this.get("status") == "Suggested") {
                this.set({"isSuggested": true, "badgeIcon": "/images/node-suggested.png?" + KA_VERSION});
            } else if (this.get("status") == "Review") {
                this.set({"isSuggested": true, "isReview": true, "badgeIcon": "/images/node-review.png?" + KA_VERSION});
            } else if (this.get("status") == "Proficient") {
                this.set({"isSuggested": false, "badgeIcon": "/images/node-complete.png?" + KA_VERSION});
            } else {
                this.set({"isSuggested": false, "badgeIcon": "/images/node-not-started.png?" + KA_VERSION});
            }

            this.set({
                inAllList: false,
                lowercaseName: this.get("display_name").toLowerCase(),
                zoomBounds: [KnowledgeMapGlobals.options.minZoom + 1, KnowledgeMapGlobals.options.maxZoom]
            });

            // TODO(kamens): remove/replace w/ simple streak bar/icon?
            this.set({"streakBar": {
                "proficient": this.get("progress") >= 1,
                "suggested": (this.get("status") == "Suggested" || (this.get("progress") < 1 && this.get("progress") > 0)),
                "progressDisplay": this.get("progress_display"),
                "maxWidth": 228,
                "width": Math.min(1.0, this.get("progress")) * 228
            }});

            return Backbone.Model.prototype.initialize.call(this, attributes);
        },

        url: function() {
            return "/exercise/" + this.get("name");
        },

        adminUrl: function() {
            return "/editexercise?name=" + this.get("name");
        }
    })

}
