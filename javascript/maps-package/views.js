
// TODO: would be nice if this were part of a larger KnowledgeMap context
// instead of needing the KnowledgeMap naming prefix.
var KnowledgeMapViews = {}

KnowledgeMapViews.ExerciseRow = Backbone.View.extend({

    initialize: function() {
        this.visible = false;
        this.nodeName = this.model.get("name");
        this.parent = this.options.parent;
    },

    events: {
        "click .exercise-title": "onBadgeClick",
        "click .proficient-badge": "onBadgeClick",
        "click .exercise-show": "onShowExerciseClick"
    },

    inflate: function() {
        if (this.inflated)
            return;

        var template = Templates.get(this.options.admin ? "shared.knowledgemap-admin-exercise" : "shared.knowledgemap-exercise");
        var context = this.model.toJSON();
        if (this.options.admin) {
            context.url = this.model.adminUrl();
        } else {
            context.url = this.model.url();
        }

        context.disabled = this.model.get("invalidForGoal") || false;

        var newContent = $(template(context));
        var self = this;
        newContent.hover(
            function() {self.onBadgeMouseover(self.nodeName, newContent);},
            function() {self.onBadgeMouseout(self.nodeName, newContent);}
        );

        this.el.replaceWith(newContent);
        this.el = newContent;
        this.inflated = true;
        this.delegateEvents();
    },

    onBadgeClick: function(evt) {
        // give the parent a chance to handle this exercise click. If it
        // doesn't, we'll just follow the anchor href
        return this.parent.nodeClickHandler(this.model, evt);
    },

    onBadgeMouseover: function(node_name, element) {
        this.parent.highlightNode(node_name, true);

        element.find(".exercise-show").show();
    },

    onBadgeMouseout: function(node_name, element) {
        this.parent.highlightNode(node_name, false);

        element.find(".exercise-show").hide();
    },

    onShowExerciseClick: function() {
        this.parent.panToNode(this.nodeName);
        this.parent.highlightNode(this.nodeName, true);
    },

    showGoalIcon: function(visible) {
        if (visible)
            this.el.find(".exercise-goal-icon").show();
        else
            this.el.find(".exercise-goal-icon").hide();
    }

});

KnowledgeMapViews.NodeMarker = Backbone.View.extend({

    initialize: function() {
        this.nodeName = this.model.get("name");
        this.filtered = false;
        this.goalIconVisible = false;
        this.parent = this.options.parent;

        this.updateElement(this.el);
    },

    updateElement: function(el) {

        this.el = el;
        this.zoom = this.parent.map.getZoom();

        if (this.model.isVisibleAtZoom(this.zoom)) {

            // Don't render nodes outside of their zoom bounds
            this.el.css("display", "none");
            return;

        } else {

            this.el.css("display", "");

        }

        var self = this;

        this.el.click(
                function(evt) {return self.onNodeClick(evt);}
            ).hover(
                function() {return self.onNodeMouseover();},
                function() {return self.onNodeMouseout();}
            );

        this.el.attr("class", this.getLabelClass());

        if (this.parent.admin)
            this.el.attr("href", this.model.adminUrl());
        else
            this.el.attr("href", this.model.url());

        if (this.goalIconVisible)
            this.el.find(".exercise-goal-icon").show();
        else
            this.el.find(".exercise-goal-icon").hide();
    },

    getLabelClass: function() {
        var classText = "nodeLabel nodeLabel" + this.model.get("status");

        classText += (" nodeLabelZoom" + this.zoom);
        classText += (this.filtered ? " nodeLabelFiltered" : "");
        classText += (this.model.get("invalidForGoal") ? " goalNodeInvalid" : "");

        return classText;
    },

    setFiltered: function(filtered, bounds) {
        if (filtered != this.filtered) {
            this.filtered = filtered;
        }

        var updateAppearance;
        if (bounds) {
            // only update appearance of nodes that are currently on screen
            var node = this.parent.dictNodes[this.nodeName];
            updateAppearance = bounds.contains(node.latLng);
        }
        else {
            updateAppearance = true;
        }

        // if we're in the window, update
        if (updateAppearance) {
            this.updateAppearance();
        }
    },

    updateAppearance: function() {
        // set class for css to apply styles
        if (this.filtered) {
            this.el.addClass("nodeLabelFiltered");
        } else {
            this.el.removeClass("nodeLabelFiltered");
        }

        // perf hack: instead of changing css opacity, set a whole new image
        var img = this.el.find('img.node-icon');
        var url = img.attr('src');

        // normalize
        if (url.indexOf("faded") >= 0) {
            url = url.replace("-faded.png", ".png");
        }

        if (this.filtered) {
            img.attr('src', url.replace(".png", "-faded.png"));
        } else {
            img.attr('src', url);
        }
    },

    showGoalIcon: function(visible) {
        if (visible != this.goalIconVisible) {
            this.goalIconVisible = visible;
            if (this.goalIconVisible)
                this.el.find(".exercise-goal-icon").show();
            else
                this.el.find(".exercise-goal-icon").hide();
        }
    },

    setHighlight: function(highlight) {
        if (highlight)
            this.el.addClass("nodeLabelHighlight");
        else
            this.el.removeClass("nodeLabelHighlight");
    },

    onNodeClick: function(evt) {
        var self = this;

        if (!this.parent.map.getZoom() <= KnowledgeMapGlobals.options.minZoom)
            return;

        if (this.parent.admin)
        {
            if (evt.shiftKey)
            {
                if (this.nodeName in this.parent.selectedNodes)
                {
                    delete this.parent.selectedNodes[this.nodeName];
                    this.parent.highlightNode(this.nodeName, false);
                }
                else
                {
                    this.parent.selectedNodes[this.nodeName] = true;
                    this.parent.highlightNode(this.nodeName, true);
                }
            }
            else
            {
                $.each(this.parent.selectedNodes, function(node_name) {
                    self.parent.highlightNode(node_name, false);
                });
                this.parent.selectedNodes = { };
                this.parent.selectedNodes[this.nodeName] = true;
                this.parent.highlightNode(this.nodeName, true);
            }

            //Unbind other keydowns to prevent a spawn of hell
            $(document).unbind("keydown");

            // If keydown is an arrow key
            $(document).keydown(function(e) {
                var delta_v = 0, delta_h = 0;

                if (e.keyCode == 37) {
                    delta_v = -1; // Left
                }
                if (e.keyCode == 38) {
                    delta_h = -1; // Up
                }
                if (e.keyCode == 39) {
                    delta_v = 1; // Right
                }
                if (e.keyCode == 40) {
                    delta_h = 1; // Down
                }

                if (delta_v != 0 || delta_h != 0) {
                    var id_array = [];

                    $.each(self.parent.selectedNodes, function(node_name) {
                        var actual_node = self.parent.dictNodes[node_name];

                        actual_node.v_position = parseInt(actual_node.v_position) + delta_v;
                        actual_node.h_position = parseInt(actual_node.h_position) + delta_h;

                        id_array.push(node_name);
                    });
                    $.post("/moveexercisemapnodes", { exercises: id_array.join(","), delta_h: delta_h, delta_v: delta_v });

                    var zoom = self.parent.map.getZoom();
                    self.parent.markers = [];

                    $.each(self.parent.dictEdges, function(key, rgTargets) { // this loop lets us update the edges wand will remove the old edges
                        for (var ix = 0; ix < rgTargets.length; ix++) {
                            var line = rgTargets[ix].line;
                            if (line != null) {
                                line.setMap(null);
                            }
                        }
                    });
                    self.parent.overlay.setMap(null);
                    self.parent.layoutGraph();
                    self.parent.drawOverlay();

                    setTimeout(function() {
                            $.each(self.parent.selectedNodes, function(node_name) {
                                self.parent.highlightNode(node_name, true);
                            });
                        }, 100);

                    return false;
                }
            });

            evt.preventDefault();
        }
        else
        {
            return this.parent.nodeClickHandler(this.model, evt);
        }
    },

    onNodeMouseover: function() {
        if (this.nodeName in this.parent.selectedNodes)
            return;

        $(".exercise-badge[data-id=\"" + this.parent.escapeSelector(this.nodeName) + "\"]").addClass("exercise-badge-hover");
        this.parent.highlightNode(this.nodeName, true);
    },

    onNodeMouseout: function() {
        if (this.nodeName in this.parent.selectedNodes)
            return;

        $(".exercise-badge[data-id=\"" + this.parent.escapeSelector(this.nodeName) + "\"]").removeClass("exercise-badge-hover");
        this.parent.highlightNode(this.nodeName, false);
    }
},
{
    extendBounds: function(bounds, dlat, dlng) {
        dlat = dlat || KnowledgeMapGlobals.nodeSpacing.lat;
        dlng = dlat || KnowledgeMapGlobals.nodeSpacing.lng;

        var ne = bounds.getNorthEast();
        var nee = new google.maps.LatLng(ne.lat() + dlat, ne.lng() + dlng);

        var sw = bounds.getSouthWest();
        var swe = new google.maps.LatLng(sw.lat() - dlat, sw.lng() - dlng);

        return new google.maps.LatLngBounds(swe, nee);
    }

});
