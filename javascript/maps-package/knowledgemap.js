var KnowledgeMapGlobals = {
    colors: {
        blue: "#0080C9",
        green: "#8EBE4F",
        red: "#E35D04",
        gray: "#FFFFFF"
    },
    icons: {
            Exercise: {
                    Proficient: "/images/node-complete.png?" + KA_VERSION,
                    Review: "/images/node-review.png?" + KA_VERSION,
                    Suggested: "/images/node-suggested.png?" + KA_VERSION,
                    Normal: "/images/node-not-started.png?" + KA_VERSION
                      },
            Summative: {
                    Normal: "/images/node-challenge-not-started.png?" + KA_VERSION,
                    Proficient: "/images/node-challenge-complete.png?" + KA_VERSION,
                    Suggested: "/images/node-challenge-suggested.png?" + KA_VERSION
                       }
    },
    latLngHome: new google.maps.LatLng(-0.064844, 0.736268),
    latMin: 90,
    latMax: -90,
    lngMin: 180,
    lngMax: -180,
    nodeSpacing: {lat: 0.392, lng: 0.35},
    options: {
                getTileUrl: function(coord, zoom) {
                    // Sky tiles example from
                    // http://gmaps-samples-v3.googlecode.com/svn/trunk/planetary-maptypes/planetary-maptypes.html
                    return KnowledgeMapGlobals.getHorizontallyRepeatingTileUrl(coord, zoom, 
                            function(coord, zoom) {
                              return "/images/map-tiles/field_" +
                                 Math.floor(Math.random()*4+1) + '.jpg';
                            }
                )},
                tileSize: new google.maps.Size(256, 256),
                maxZoom: 10,
                minZoom: 7,
                isPng: false
    },
    getHorizontallyRepeatingTileUrl: function(coord, zoom, urlfunc) {

        // From http://gmaps-samples-v3.googlecode.com/svn/trunk/planetary-maptypes/planetary-maptypes.html
        var y = coord.y;
        var x = coord.x;

        // tile range in one direction range is dependent on zoom level
        // 0 = 1 tile, 1 = 2 tiles, 2 = 4 tiles, 3 = 8 tiles, etc
        var tileRange = 1 << zoom;

        // don't repeat across y-axis (vertically)
        if (y < 0 || y >= tileRange) {
            return null;
        }

        // repeat across x-axis
        if (x < 0 || x >= tileRange) {
            x = (x % tileRange + tileRange) % tileRange;
        }

        return urlfunc({x:x,y:y}, zoom);
    }
};

var KnowledgeMapExercise = Backbone.Model.extend({
    initialize: function() {
        var s_prefix = this.get('summative') ? 'node-challenge' : 'node'; // TomY TODO ?App.version

        if (this.get('status') == 'Suggested') {
            this.set({'isSuggested': true, 'badgeIcon': '/images/'+s_prefix+'-suggested.png'});
        } else if (this.get('status') == 'Review') {
            this.set({'isSuggested': true, 'isReview': true, 'badgeIcon': '/images/node-review.png'});
        } else if (this.get('status') == 'Proficient') {
            this.set({'isSuggested': false, 'badgeIcon': '/images/'+s_prefix+'-complete.png'});
        } else {
            this.set({'isSuggested': false, 'badgeIcon': '/images/'+s_prefix+'-not-started.png'});
        }

        this.set({'inAllList': false, 'lowercaseName': this.get('display_name').toLowerCase()});

        var milestones = [];
        for (var milestone = 0; milestone < this.get('num_milestones')-1; milestone++) {
            milestones.push({
                'left': Math.round((milestone+1)*(228/this.get('num_milestones'))),
            });
        }
        this.set({'streakBar': {
            'proficient': this.get('progress') >= 1,
            'suggested': (this.get('status') == 'Suggested' || (this.get('progress') < 1 && this.get('progress') > 0)),
            'progressDisplay': this.get('progress_display'),
            'maxWidth': 228,
            'width': Math.min(1.0, this.get('progress'))*228,
            'milestones': [],
        }});
    }
});

var ExerciseRowView = Backbone.View.extend({
    initialize: function() {
        this.visible = false;
        this.nodeName = this.model.get('name');
        this.parent = this.options.parent;

        this.parent.filterSettings.bind('change', this.doFilter, this);
    },

    events: {
        "click .exercise-title":    "onBadgeClick",
        "click .proficient-badge":  "onBadgeClick",
        "click .exercise-show":     "onShowExerciseClick"
    },

    inflate: function() {
        if (this.inflated)
            return;

        var template = Templates.get( this.options.admin ? "knowledgemap-admin-exercise" : "knowledgemap-exercise" );
        var newContent = $(template(this.model.toJSON()));
        var self = this;
        newContent.hover(
                function(){self.onBadgeMouseover(self.nodeName, newContent);},
                function(){self.onBadgeMouseout(self.nodeName, newContent);}
        );

        this.el.replaceWith(newContent);
        this.el = newContent;
        this.inflated = true;
        this.delegateEvents();
    },

    doFilter: function() {
        var filterText = this.parent.filterSettings.get('filterText');
        var filterMatches = (this.model.get('lowercaseName').indexOf(filterText) >= 0);
        var allowVisible = this.options.type != 'all' || filterText || this.parent.filterSettings.get('userShowAll');

        this.visible = allowVisible && filterMatches;
        if (this.visible) {
            if (!this.inflated) {
                this.inflate();
            }
            this.el.show();
        } else {
            this.el.hide();
        }

        if (this.options.type == 'all' && this.parent.exerciseMarkerViews[this.nodeName]) {
            this.parent.exerciseMarkerViews[this.nodeName].setFiltered(!filterMatches);
        }
    },

    onBadgeClick: function(evt) {
        this.parent.nodeClickHandler(this.model, evt);
    },

    onBadgeMouseover: function(node_name, element) {
        this.parent.highlightNode(node_name, true);

        element.find('.exercise-show').show();
    },

    onBadgeMouseout: function(node_name, element) {
        this.parent.highlightNode(node_name, false);

        element.find('.exercise-show').hide();
    },

    onShowExerciseClick: function() {
        this.parent.panToNode(this.nodeName);
        this.parent.highlightNode(this.nodeName, true);
    },

    showGoalIcon: function(visible) {
        if (visible)
            this.el.find('.exercise-goal-icon').show();
        else
            this.el.find('.exercise-goal-icon').hide();
    }
});
var ExerciseMarkerView = Backbone.View.extend({
    initialize: function() {
        var exercise = this.model;
        this.nodeName = exercise.get('name');
        this.filtered = false;
        this.goalIconVisible = false;
        this.parent = this.options.parent;

        var iconSet = KnowledgeMapGlobals.icons[exercise.get('summative') ? "Summative" : "Exercise"];
        this.iconUrl = iconSet[exercise.get('status')];
        if (!this.iconUrl) this.iconUrl = iconSet.Normal;

        this.updateElement(this.el);
    },
    updateElement: function(el) {
        this.el = el;
        this.zoom = this.parent.map.getZoom();
        var self = this;

        this.el.click(
                function(evt){self.onNodeClick(evt);}
            ).hover(
                function(){self.onNodeMouseover();},
                function(){self.onNodeMouseout();}
            );

        var iconOptions = this.getIconOptions();
        this.el.find("img.node-icon").attr("src", iconOptions.url);
        this.el.attr("class", this.getLabelClass());
        if (this.goalIconVisible)
            this.el.find('.exercise-goal-icon').show();
        else
            this.el.find('.exercise-goal-icon').hide();
    },

    getIconOptions: function() {

        var iconUrlCacheKey = this.iconUrl + "@" + this.zoom;

        if (!this.parent.iconCache) this.parent.iconCache = {};
        if (!this.parent.iconCache[iconUrlCacheKey])
        {
            var url = this.iconUrl;

            if (!this.model.get('summative') && this.zoom <= KnowledgeMapGlobals.options.minZoom)
            {
                url = this.iconUrl.replace(".png", "-star.png");
            }

            this.parent.iconCache[iconUrlCacheKey] = {url: url};
        }
        return this.parent.iconCache[iconUrlCacheKey];
    },

    getLabelClass: function() {
        var classText = "nodeLabel nodeLabel" + this.model.get('status');
        var visible = !this.model.get('summative') || this.zoom == KnowledgeMapGlobals.options.minZoom;
        if (this.model.get('summative') && visible) this.zoom = KnowledgeMapGlobals.options.maxZoom - 1;

        if (this.model.get('summative')) classText += " nodeLabelSummative";
        classText += (visible ? "" : " nodeLabelHidden");
        classText += (" nodeLabelZoom" + this.zoom);
        classText += (this.filtered ? " nodeLabelFiltered" : "");

        return classText;
    },

    setFiltered: function(filtered) {
        if (filtered != this.filtered) {
            this.filtered = filtered;
            if (this.filtered)
                this.el.addClass('nodeLabelFiltered');
            else
                this.el.removeClass('nodeLabelFiltered');
        }
    },

    showGoalIcon: function(visible) {
        if (visible != this.goalIconVisible) {
            this.goalIconVisible = visible;
            if (this.goalIconVisible)
                this.el.find('.exercise-goal-icon').show();
            else
                this.el.find('.exercise-goal-icon').hide();
        }
    },

    onNodeClick: function(evt) {
        if (!this.model.get('summative') && this.parent.map.getZoom() <= KnowledgeMapGlobals.options.minZoom)
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
                    this.parent.highlightNode(node_name, false);
                });
                this.parent.selectedNodes = { };
                this.parent.selectedNodes[this.nodeName] = true;
                this.parent.highlightNode(this.nodeName, true);
            }
            
            //Unbind other keydowns to prevent a spawn of hell
            $(document).unbind('keydown');

            // If keydown is an arrow key
            $(document).keydown(function(e){
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

                    $.each(this.parent.selectedNodes, function(node_name) {
                        var actual_node = this.parent.dictNodes[node_name];

                        actual_node.v_position = parseInt(actual_node.v_position) + delta_v;
                        actual_node.h_position = parseInt(actual_node.h_position) + delta_h;

                        id_array.push(node_name);
                    });
                    $.post("/moveexercisemapnodes", { exercises: id_array.join(","), delta_h: delta_h, delta_v: delta_v } );

                    var zoom =this.parent.map.getZoom();
                    this.parent.markers = [];

                    for (var key in this.parent.dictEdges) // this loop lets us update the edges wand will remove the old edges
                    {
                        var rgTargets = this.parent.dictEdges[key];
                        for (var ix = 0; ix < rgTargets.length; ix++)
                        {
                            rgTargets[ix].line.setMap(null);
                        }
                    }
                    this.parent.overlay.setMap(null);
                    this.parent.layoutGraph();
                    this.parent.drawOverlay();

                    setTimeout(function() {
                            $.each(this.parent.selectedNodes, function(node_name) {
                                this.parent.highlightNode(node_name, true);
                            });
                        }, 100);

                    return false;
                }
            });
            
            evt.stopPropagation();
        }
        else
        {
            this.parent.nodeClickHandler(this.model, evt);
        }
    },

    onNodeMouseover: function() {
        if (!this.model.get('summative') && this.parent.map.getZoom() <= KnowledgeMapGlobals.options.minZoom)
            return;
        if (this.nodeName in this.parent.selectedNodes)
            return;
      
        $(".exercise-badge[data-id=\"" + this.parent.escapeSelector(this.nodeName) + "\"]").addClass("exercise-badge-hover");
        this.parent.highlightNode(this.nodeName, true);
    },

    onNodeMouseout: function() {
        if (!this.model.get('summative') && this.parent.map.getZoom() <= KnowledgeMapGlobals.options.minZoom)
            return;
        if (this.nodeName in this.parent.selectedNodes)
            return;
    
        $(".exercise-badge[data-id=\"" + this.parent.escapeSelector(this.nodeName) + "\"]").removeClass("exercise-badge-hover");
        this.parent.highlightNode(this.nodeName, false);
    },
});

function KnowledgeMap(params) {

    var self = this;

    this.selectedNodes = {};
    this.nodeClickHandler = null;
    this.updateFilterTimout = null;

    // Models
    this.exerciseList = {};
    this.filterSettings = new Backbone.Model({'filterText': '---', 'userShowAll': false});
    this.numSuggestedExercises = 0;
    this.numRecentExercises = 0;

    // Views
    this.exerciseRowViews = [];
    this.exerciseMarkerViews = {},

    // Map
    this.map = null;
    this.overlay = null;
    this.dictNodes = {};
    this.dictEdges = [];
    this.markers = [];
    this.latLngBounds = null;
    this.fFirstDraw = true;
    this.fCenterChanged = false;
    this.fZoomChanged = false;

    this.admin = !!params.admin;

    this.init = function(params) {
        this.containerID = (!!params.container) ? ('#' + params.container) : null;
        this.elementTable = {};

        this.drawer = new Drawer(params.container, this); 

        var suggestedExercisesContent = this.admin ? null : this.getElement('suggested-exercises-content');
        var recentExercisesContent = this.admin ? null : this.getElement('recent-exercises-content');
        var allExercisesContent = this.getElement('all-exercises-content');

        if (!this.admin) {
            self.getElement('exercise-all-exercises').click(function() { self.toggleShowAll(); });
        }

        this.filterSettings.set({'userShowAll': this.admin});

		Handlebars.registerPartial('streak-bar', Templates.get( "streak-bar" )); // TomY TODO do this automatically?
		Handlebars.registerPartial('knowledgemap-exercise', Templates.get( "knowledgemap-exercise" )); // TomY TODO do this automatically?

        // Initial setup of exercise list from embedded data

        $.each(graph_dict_data, function(idx, exercise) {

            var exerciseModel = new KnowledgeMapExercise(exercise);
            self.exerciseList[exercise.name] = exerciseModel;

            // Create views

            if (exerciseModel.get('isSuggested')) {
                if (!params.hideReview || !exerciseModel.get('isReview')) {
                    var element = $('<div>');
                    element.appendTo(suggestedExercisesContent);
                    self.exerciseRowViews.push(new ExerciseRowView({'model': exerciseModel, 'el': element, 'type': 'suggested', 'admin': self.admin, 'parent': self}));

                    self.numSuggestedExercises++;
                }
            }
            
            if (exerciseModel.get('recent')) {
                var element = $('<div>');
                element.appendTo(recentExercisesContent);
                self.exerciseRowViews.push(new ExerciseRowView({'model': exerciseModel, 'el': element, 'type': 'recent', 'admin': self.admin, 'parent': self}));

                self.numRecentExercises++;
            }

            var element = $('<div>');
            element.appendTo(allExercisesContent);
            self.exerciseRowViews.push(new ExerciseRowView({'model': exerciseModel, 'el': element, 'type': 'all', 'admin': self.admin, 'parent': self}));

            // Update map graph

            self.addNode(exerciseModel.toJSON());
            $.each(exerciseModel.get('prereqs'), function(idx2, prereq) {
                self.addEdge(exerciseModel.get('name'), prereq, exerciseModel.get('summative'));
            });
        });

        var mapElement = self.getElement("map-canvas"); 
        this.map = new google.maps.Map(mapElement.get(0), {
            mapTypeControl: false,
            streetViewControl: false,
            scrollwheel: false
        });

        var knowledgeMapType = new google.maps.ImageMapType(KnowledgeMapGlobals.options);
        this.map.mapTypes.set('knowledge', knowledgeMapType);
        this.map.setMapTypeId('knowledge');

        if (params.mapCoords)
        {
            this.map.setCenter(new google.maps.LatLng(params.mapCoords[0], params.mapCoords[1]));
            this.map.setZoom(params.mapCoords[2]);
        }
        else
        {
            this.map.setCenter(this.latLngHome);
            this.map.setZoom(KnowledgeMapGlobals.options.minZoom + 2);
        }

        this.layoutGraph();
        this.drawOverlay();

        this.latLngBounds = new google.maps.LatLngBounds(new google.maps.LatLng(KnowledgeMapGlobals.latMin, KnowledgeMapGlobals.lngMin), new google.maps.LatLng(KnowledgeMapGlobals.latMax, KnowledgeMapGlobals.lngMax)),

        google.maps.event.addListener(this.map, "center_changed", function(){self.onCenterChange();});
        google.maps.event.addListener(this.map, "idle", function(){self.onIdle();});
        google.maps.event.addListener(this.map, "click", function(){self.onClick();});

        this.nodeClickHandler = function(exercise) {
            if (self.admin)
                window.location.href = '/editexercise?name='+exercise.get('name');
            else
                window.location.href = '/exercises?exid='+exercise.get('name');
        };

        this.giveNasaCredit();
        this.initFilter();
    };

    this.setNodeClickHandler = function(click_handler) {
        this.nodeClickHandler = click_handler;
    };

    this.panToNode = function(dataID) {
        var node = this.dictNodes[dataID];

        // Set appropriate zoom level if necessary
        if (node.summative && this.map.getZoom() > KnowledgeMapGlobals.options.minZoom)
            this.map.setZoom(KnowledgeMapGlobals.options.minZoom);
        else if (!node.summative && this.map.getZoom() == KnowledgeMapGlobals.options.minZoom)
            this.map.setZoom(KnowledgeMapGlobals.options.minZoom+1);

        // Move the node to the center of the view
        this.map.panTo(node.latLng);
    };

    this.escapeSelector = function(s) {
        return s.replace(/(:|\.)/g,'\\$1');
    };

    this.giveNasaCredit = function() {
        // Setup a copyright/credit line, emulating the standard Google style
        // From
        // http://code.google.com/apis/maps/documentation/javascript/demogallery.html?searchquery=Planetary
        var creditNode = $("<div class='creditLabel'>Image Credit: SDSS, DSS Consortium, NASA/ESA/STScI</div>");
        creditNode[0].index = 0;
        this.map.controls[google.maps.ControlPosition.BOTTOM_RIGHT].push(creditNode[0]);
    };

    this.layoutGraph = function() {

        var zoom = this.map.getZoom();

        for (var key in this.dictNodes)
        {
            this.drawMarker(this.dictNodes[key], zoom);
        }

        for (var key in this.dictEdges)
        {
            var rgTargets = this.dictEdges[key];
            for (var ix = 0; ix < rgTargets.length; ix++)
            {
                this.drawEdge(this.dictNodes[key], rgTargets[ix], zoom);
            }
        }
    };

    this.drawOverlay = function() {
        this.overlay = new com.redfin.FastMarkerOverlay(this.map, this.markers);
        this.overlay.drawOriginal = this.overlay.draw;
        this.overlay.draw = function() {
            this.drawOriginal();

            var jrgNodes = $(".nodeLabel");

            if (!self.fFirstDraw)
            {
                self.onZoomChange(jrgNodes);
            }

            jrgNodes.each(function(){
                var exerciseName = $(this).attr("data-id");
                var exercise = self.exerciseList[exerciseName];
                var view = self.exerciseMarkerViews[exerciseName];
                if (view) {
                    view.updateElement($(this));
                } else {
                    view = new ExerciseMarkerView({'model': exercise, 'el': $(this), 'parent': self});
                    self.exerciseMarkerViews[exerciseName] = view;
                }
            });

            self.fFirstDraw = false;
        }
    };

    this.addNode = function(node) {
        this.dictNodes[node.name] = node;
    };

    this.addEdge = function(source, target, summative) {
        if (!this.dictEdges[source]) this.dictEdges[source] = [];
        var rg = this.dictEdges[source];
        rg[rg.length] = {"target": target, "summative": summative};
    };

    this.nodeStatusCount = function(status) {
        var c = 0;
        for (var ix = 1; ix < arguments.length; ix++)
        {
            if (arguments[ix].status == status) c++;
        }
        return c;
    };

    this.drawEdge = function(nodeSource, edgeTarget, zoom) {

        var nodeTarget = this.dictNodes[edgeTarget.target];

        // If either of the nodes is missing, don't draw the edge.
        if (!nodeSource || !nodeTarget) return;

        var coordinates = [
            nodeSource.latLng,
            nodeTarget.latLng
        ];

        var countProficient = this.nodeStatusCount("Proficient", nodeSource, nodeTarget);
        var countSuggested = this.nodeStatusCount("Suggested", nodeSource, nodeTarget);
        var countReview = this.nodeStatusCount("Review", nodeSource, nodeTarget);

        var color = KnowledgeMapGlobals.colors.gray;
        var weight = 1.0;
        var opacity = 0.48;

        if (countProficient == 2)
        {
            color = KnowledgeMapGlobals.colors.blue;
            weight = 5.0;
            opacity = 1.0;
        }
        else if (countProficient == 1 && countSuggested == 1)
        {
            color = KnowledgeMapGlobals.colors.green;
            weight = 5.0;
            opacity = 1.0;
        }
        else if (countReview > 0)
        {
            color = KnowledgeMapGlobals.colors.red;
            weight = 5.0;
            opacity = 1.0;
        }

        edgeTarget.line = new google.maps.Polyline({
            path: coordinates,
            strokeColor: color,
            strokeOpacity: opacity,
            strokeWeight: weight,
            clickable: false,
            map: this.getMapForEdge(edgeTarget, zoom)
        });
    };

    this.drawMarker = function(node, zoom) {

        var lat = -1 * (node.h_position - 1) * KnowledgeMapGlobals.nodeSpacing.lat;
        var lng = (node.v_position - 1) * KnowledgeMapGlobals.nodeSpacing.lng;

        node.latLng = new google.maps.LatLng(lat, lng);

        if (lat < KnowledgeMapGlobals.latMin) KnowledgeMapGlobals.latMin = lat;
        if (lat > KnowledgeMapGlobals.latMax) KnowledgeMapGlobals.latMax = lat;
        if (lng < KnowledgeMapGlobals.lngMin) KnowledgeMapGlobals.lngMin = lng;
        if (lng > KnowledgeMapGlobals.lngMax) KnowledgeMapGlobals.lngMax = lng;

        var marker = new com.redfin.FastMarker(
                "marker-" + node.name, 
                node.latLng, 
                ["<div id='node-" + node.name + "' data-id='" + node.name + "' class='nodeLabel'><img class='node-icon' src=''/><img class='exercise-goal-icon' style='display: none' src='/images/flag.png'/><div>" + node.display_name + "</div></div>"], 
                "", 
                node.summative ? 2 : 1,
                0,0);

        this.markers[this.markers.length] = marker;
    };

    this.getMapForEdge = function(edge, zoom) {
        return ((zoom == KnowledgeMapGlobals.options.minZoom) == edge.summative) ? this.map : null;
    };

    this.highlightNode = function(node_name, highlight) {
        var jel = $("#node-" + this.escapeSelector(node_name));
        if (highlight)
            jel.addClass("nodeLabelHighlight");
        else
            jel.removeClass("nodeLabelHighlight");
    };

    this.onZoomChange = function() {

        var zoom = this.map.getZoom();

        if (zoom < KnowledgeMapGlobals.options.minZoom) return;
        if (zoom > KnowledgeMapGlobals.options.maxZoom) return;

        this.fZoomChanged = true;

        for (var key in this.dictEdges)
        {
            var rgTargets = this.dictEdges[key];
            for (var ix = 0; ix < rgTargets.length; ix++)
            {
                var line = rgTargets[ix].line;
                var map = this.getMapForEdge(rgTargets[ix], zoom);
                if (line.getMap() != map) line.setMap(map);
            }
        }
    };

    this.onIdle = function() {

        if (!this.fCenterChanged && !this.fZoomChanged)
            return;

        // Panning by 0 pixels forces a redraw of our map's markers
        // in case they aren't being rendered at the correct size.
        this.map.panBy(0, 0);

        var center = this.map.getCenter();
        $.post("/savemapcoords", {
            "lat": center.lat(),
            "lng": center.lng(),
            "zoom": this.map.getZoom()
        }); // Fire and forget
    };

    this.onClick = function() {
        if (this.admin) {
            $.each(this.selectedNodes, function(node_name) {
                self.highlightNode(self.dictNodes[node_name], false);
            });
            self.selectedNodes = { };
        }
    };

    this.onCenterChange = function() {

        this.fCenterChanged = true;

        var center = this.map.getCenter();
        if (this.latLngBounds.contains(center)) {
            return;
        }

        var C = center;
        var X = C.lng();
        var Y = C.lat();

        var AmaxX = this.latLngBounds.getNorthEast().lng();
        var AmaxY = this.latLngBounds.getNorthEast().lat();
        var AminX = this.latLngBounds.getSouthWest().lng();
        var AminY = this.latLngBounds.getSouthWest().lat();

        if (X < AminX) {X = AminX;}
        if (X > AmaxX) {X = AmaxX;}
        if (Y < AminY) {Y = AminY;}
        if (Y > AmaxY) {Y = AmaxY;}

        this.map.setCenter(new google.maps.LatLng(Y,X));
    };

    // Filtering

    this.initFilter = function() {
        self.getElement('dashboard-filter-text').keyup(function() {
            if (self.updateFilterTimeout == null) {
                self.updateFilterTimeout = setTimeout(function() {
                    self.updateFilter();
                    self.updateFilterTimeout = null;
                }, 250);
            }
        }).placeholder();
        
        self.getElement('dashboard-filter-clear').click(function() {
            self.clearFilter();
        });
        this.clearFilter();
    };

    this.clearFilter = function() {
        self.getElement('dashboard-filter-text').val('');
        this.updateFilter();
    };

    this.updateFilter = function() {
        var filterText = $.trim(self.getElement('dashboard-filter-text').val().toLowerCase());

        // Temporarily remove the exercise list container div for better performance
        var reattachFn = temporaryDetachElement(self.getElement('exercise-list'));

        self.filterSettings.set({'filterText': filterText});

        // Re-insert the container div
        reattachFn();

        this.postUpdateFilter();
    };

    this.toggleShowAll = function() {
        this.filterSettings.set({'userShowAll': !self.filterSettings.get('userShowAll')});
        this.postUpdateFilter();
    };

    this.postUpdateFilter = function() {
        var counts = { 'suggested':0, 'recent':0, 'all':0 };
        var filterText = self.filterSettings.get('filterText');

        $.each(self.exerciseRowViews, function(idx, exerciseRowView) {
            if (exerciseRowView.visible)
                counts[exerciseRowView.options.type]++;
        });

        if (!self.admin) {
            if (counts.suggested > 0) {
                self.getElement('dashboard-suggested-exercises').find('.exercise-filter-count').html('(Showing ' + counts.suggested + ' of ' + self.numSuggestedExercises + ')');
                self.getElement('dashboard-suggested-exercises').show();
            } else {
                self.getElement('dashboard-suggested-exercises').hide();
            }
            if (counts.recent > 0) {
                self.getElement('dashboard-recent-exercises').find('.exercise-filter-count').html('(Showing ' + counts.recent + ' of ' + self.numRecentExercises + ')');
                self.getElement('dashboard-recent-exercises').show();
            } else {
                self.getElement('dashboard-recent-exercises').hide();
            }
        }
        if (filterText && counts.all == 0) {
            self.getElement('exercise-no-results').show();
        } else {
            self.getElement('exercise-no-results').hide();
        }

        if (filterText) {
            self.getElement('dashboard-filter-clear').show();
            if (!self.admin)
                self.getElement('exercise-all-exercises').hide();
            self.getElement('dashboard-all-exercises').find('.exercise-filter-count').html('(Showing ' + counts.all + ' of ' + graph_dict_data.length + ')').show();
        } else {
            self.getElement('dashboard-filter-clear').hide();
            self.getElement('dashboard-all-exercises').find('.exercise-filter-count').hide();
            if (!self.admin) {
                self.getElement('exercise-all-exercises').show();
                self.getElement('exercise-all-exercises-text').html(self.filterSettings.get('userShowAll') ? "Hide All" : "Show All");
            }
        }
    };

    this.getElement = function(id) {
        if (this.elementTable[id])
            return this.elementTable[id];
        var el = null;
        if (this.containerID)
            el = $(this.containerID + ' .' + id);
        else
            el = $('.' + id);    
        this.elementTable[id] = el;
        if (el.length == 0)
            throw new Error('Missing element: "' + id + '" in container "' + this.containerID + '"');
        return el;
    };

    this.init(params);
};
