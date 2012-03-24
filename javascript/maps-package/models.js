
// TODO: would be nice if this were part of a larger KnowledgeMap context
// instead of needing the KnowledgeMap naming prefix.
var KnowledgeMapModels = {

    Topic: Backbone.Model.extend({

        initialize: function() {

            this.set({
                name: this.get("key_name"),
                h_position: this.get("x"),
                v_position: this.get("y"),
            });

        }

    }),

    Exercise: Backbone.Model.extend({
        initialize: function() {

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
                lowercaseName: this.get("display_name").toLowerCase()
            });

            this.set({"streakBar": {
                "proficient": this.get("progress") >= 1,
                "suggested": (this.get("status") == "Suggested" || (this.get("progress") < 1 && this.get("progress") > 0)),
                "progressDisplay": this.get("progress_display"),
                "maxWidth": 228,
                "width": Math.min(1.0, this.get("progress")) * 228
            }});
        },

        url: function() {
            return "/exercise/" + this.get("name");
        },

        adminUrl: function() {
            return "/editexercise?name=" + this.get("name");
        }
    })

}
