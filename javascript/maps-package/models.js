
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
            x: x,
            y: y,
            display_name: display_name,
            lowercaseName: display_name.toLowerCase(),
            inAllList: false, // TODO(kamens): remove?
            iconUrl: iconUrl,
            zoomBounds: zoomBounds
        });

    },

    isVisibleAtZoom: function(zoom) {
        return zoom < this.get("zoomBounds")[0] || zoom > this.get("zoomBounds")[1];
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

        this.set({
            isSuggested: this.get("states")["suggested"] || this.get("states")["reviewing"]
        });

        // Translate exercise properties to standard node properties
        this.setNodeAttrs(
            this.get("name"),
            this.get("display_name"),
            this.get("v_position"), // v_position is actually x
            this.get("h_position"), // h_position is actually y
            KnowledgeMapGlobals.icons.Exercise[this.get("status")] || KnowledgeMapGlobals.icons.Exercise.Normal,
            [KnowledgeMapGlobals.options.minZoom + 1, KnowledgeMapGlobals.options.maxZoom]
        );

        return KnowledgeMapModels.Node.prototype.initialize.call(this, attributes);
    },

    url: function() {
        return "/exercise/" + this.get("name");
    },

    adminUrl: function() {
        return "/editexercise?name=" + this.get("name");
    }

});

/**
 * Polyline represents a collection of line points for drawing paths on the map
 */
KnowledgeMapModels.Polyline = Backbone.Model.extend({

    initialize: function(attributes) {

        // Convert line path to appropriate lat/lng coord path
        this.set({
            latLngPath: _.map(this.get("path"), function(pt) {
                return KnowledgeMapGlobals.xyToLatLng(pt.x, pt.y);
            })
        });

        return Backbone.Model.prototype.initialize.call(this, attributes);
    }

});
