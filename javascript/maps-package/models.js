
// TODO: would be nice if this were part of a larger KnowledgeMap context
// instead of needing the KnowledgeMap naming prefix.

/**
 * All models that may be represented on the knowledge map
 */
var KnowledgeMapModels = {};

/**
 * All models rendered as nodes on the knowledge map extend Node
 */
KnowledgeMapModels.Node = Backbone.Model.extend({

    /**
     * Set all required properties for rendering map node
     */
    setNodeAttrs: function(name, display_name, x, y, iconUrl, zoomBounds) {

        this.set({
            name: name,
            h_position: x,
            v_position: y,
            display_name: display_name,
            lowercaseName: display_name.toLowerCase(),
            inAllList: false, // TODO(kamens): remove?
            iconUrl: iconUrl,
            zoomBounds: zoomBounds
        });

    }

});

KnowledgeMapModels.Topic = KnowledgeMapModels.Node.extend({

    initialize: function(attributes) {

        // Translate topic properties to standard node properties
        this.setNodeAttrs(
            this.get("id"),
            this.get("standalone_title"),
            this.get("x"),
            this.get("y"),
            this.get("icon_url"),
            [KnowledgeMapGlobals.options.minZoom, KnowledgeMapGlobals.options.minZoom]
        );

        return KnowledgeMapModels.Node.prototype.initialize.call(this, attributes);

    },

    url: function() {
        return "/topicexercise/" + this.get("id");
    }

});

KnowledgeMapModels.Exercise = KnowledgeMapModels.Node.extend({

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

        // Translate exercise properties to standard node properties
        this.setNodeAttrs(
            this.get("name"),
            this.get("display_name"),
            this.get("h_position"),
            this.get("v_position"),
            KnowledgeMapGlobals.icons.Exercise[this.get("status")] || KnowledgeMapGlobals.icons.Exercise.Normal,
            [KnowledgeMapGlobals.options.minZoom + 1, KnowledgeMapGlobals.options.maxZoom]
        );

        // TODO(kamens): remove/replace w/ simple streak bar/icon?
        this.set({"streakBar": {
            "proficient": this.get("progress") >= 1,
            "suggested": (this.get("status") == "Suggested" || (this.get("progress") < 1 && this.get("progress") > 0)),
            "progressDisplay": this.get("progress_display"),
            "maxWidth": 228,
            "width": Math.min(1.0, this.get("progress")) * 228
        }});

        return KnowledgeMapModels.Node.prototype.initialize.call(this, attributes);
    },

    url: function() {
        return "/exercise/" + this.get("name");
    },

    adminUrl: function() {
        return "/editexercise?name=" + this.get("name");
    }

});
