/**
 * Code to handle the logic for the profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

var Profile = {
    version: 0,
    initialGraphUrl: null, // Filled in by the template after script load.
    email: null,  // Filled in by the template after script load.
    fLoadingGraph: false,
    fLoadedGraph: false,

    init: function() {

		$('.share-link').hide();
		$('.sharepop').hide();

		$(".achievement,.exercise,.video").hover(
			function () {
			    $(this).find(".share-link").show();
				},
			function () {
			    $(this).find(".share-link").hide();
				$(this).find(".sharepop").hide();
			  });

		$('.share-link').click(function() {
			if ( $.browser.msie && (parseInt($.browser.version, 10) < 8) ) {
				$(this).next(".sharepop").toggle();
			} else {
				$(this).next(".sharepop").toggle(
						"drop", { direction:'up' }, "fast" );
			}
			return false;
		});

		// Init Highcharts global options.
		Highcharts.setOptions({
			credits: {
				enabled: false
			},
			title: {
				text: ''
			},
			subtitle: {
				text: ''
			}
		});

        if ($.address)
            $.address.externalChange(function(){ Profile.historyChange(); });

        $(".graph-link").click(function(){Profile.loadGraphFromLink(this); return false;});

        $("#individual_report #achievements #achievement-list > ul li").click(function() {
             var category = $(this).attr('id');
             var clickedBadge = $(this);

             $("#badge-container").css("display", "");
             clickedBadge.siblings().removeClass("selected");

             if ($("#badge-container > #" + category ).is(":visible")) {
                if (clickedBadge.parents().hasClass("standard-view")) {
                    $("#badge-container > #" + category ).slideUp(300, function(){
                            $("#badge-container").css("display", "none");
                            clickedBadge.removeClass("selected");
                        });
                }
                else {
                    $("#badge-container > #" + category ).hide();
                    $("#badge-container").css("display", "none");
                    clickedBadge.removeClass("selected");
                }
             }
             else {
                var jelContainer = $("#badge-container");
                var oldHeight = jelContainer.height();
                $(jelContainer).children().hide();
                if (clickedBadge.parents().hasClass("standard-view")) {
                    $(jelContainer).css("min-height", oldHeight);
                    $("#" + category, jelContainer).slideDown(300, function() {
                        $(jelContainer).animate({"min-height": 0}, 200);
                    });
                } else {
                    $("#" + category, jelContainer).show();
                }
                clickedBadge.addClass("selected");
             }
        });

        $("#stats-nav #nav-accordion").accordion({ header:".header", active:".graph-link-selected", autoHeight: false, clearStyle: true });

        setTimeout(function(){
            if (!Profile.fLoadingGraph && !Profile.fLoadedGraph)
            {
                // If 1000 millis after document.ready fires we still haven't
                // started loading a graph, load manually.
                // The externalChange trigger may have fired before we hooked
                // up a listener.
                Profile.historyChange();
            }
        }, 1000);
    },


    highlightPoints: function(chart, fxnHighlight) {

        if (!chart) return;

        for (var ix = 0; ix < chart.series.length; ix++) {
            var series = chart.series[ix];

            this.muteSeriesStyles(series);

            for (var ixData = 0; ixData < series.data.length; ixData++) {
                var pointOptions = series.data[ixData].options;
                if (!pointOptions.marker) pointOptions.marker = {};
                pointOptions.marker.enabled = fxnHighlight(pointOptions);
                if (pointOptions.marker.enabled) pointOptions.marker.radius = 6;
            }

            series.isDirty = true;
        }

        chart.redraw();
    },

    muteSeriesStyles: function(series) {
        if (series.options.fMuted) return;

        series.graph.attr('opacity', 0.1);
        series.graph.attr('stroke', '#CCCCCC');
        series.options.lineWidth = 1;
        series.options.shadow = false;
        series.options.fMuted = true;
    },

    accentuateSeriesStyles: function(series) {
        series.options.lineWidth = 3.5;
        series.options.shadow = true;
        series.options.fMuted = false;
    },

    highlightSeries: function(chart, seriesHighlight) {

        if (!chart || !seriesHighlight) return;

        for (var ix = 0; ix < chart.series.length; ix++)
        {
            var series = chart.series[ix];
            var fSelected = (series == seriesHighlight);

            if (series.fSelectedLast == null || series.fSelectedLast != fSelected)
            {
                if (fSelected)
                    this.accentuateSeriesStyles(series);
                else
                    this.muteSeriesStyles(series);

                for (var ixData = 0; ixData < series.data.length; ixData++) {
                    series.data[ixData].options.marker = {
                        enabled: fSelected,
                        radius: fSelected ? 5 : 4
                    };
                }

                series.isDirty = true;
                series.fSelectedLast = fSelected;
            }
        }

        var options = seriesHighlight.options;
        options.color = '#0080C9';
        seriesHighlight.remove(false);
        chart.addSeries(options, false, false);

        chart.redraw();
    },

    collapseAccordion: function() {
        // Turn on collapsing, collapse everything, and turn off collapsing
        $("#stats-nav #nav-accordion").accordion(
                "option", "collapsible", true).accordion(
                    "activate", false).accordion(
                        "option", "collapsible", false);
    },

    baseGraphHref: function(href) {
        // regex for matching scheme:// part of uri
        // see http://tools.ietf.org/html/rfc3986#section-3.1
        var reScheme = /^\w[\w\d+-.]*:\/\//;
        var match = href.match(reScheme);
        if (match) {
            href = href.substring(match[0].length);
        }

        var ixSlash = href.indexOf("/");
        if (ixSlash > -1)
            href = href.substring(href.indexOf("/"));

        var ixQuestionMark = href.indexOf("?");
        if (ixQuestionMark > -1)
            href = href.substring(0, ixQuestionMark);

        return href;
    },

	/**
	 * Expands the navigation accordion according to the link specified.
	 * @return {boolean} whether or not a link was found to be a valid link.
	 */
	expandAccordionForHref: function(href) {
		if (!href) {
			return false;
		}

		href = this.baseGraphHref(href);

		href = href.replace(/[<>']/g, "");
		var selectorAccordionSection =
				".graph-link-header[href*='" + href + "']";
		if ( $(selectorAccordionSection).length ) {
			$("#stats-nav #nav-accordion").accordion(
					"activate", selectorAccordionSection);
			return true;
		}

		this.collapseAccordion();
		return false;
	},

    styleSublinkFromHref: function(href) {

        if (!href) return;

        var reDtStart = /dt_start=[^&]+/;

        var matchStart = href.match(reDtStart);
        var sDtStart = matchStart ? matchStart[0] : "dt_start=lastweek";

        href = href.replace(/[<>']/g, "");

        $(".graph-sub-link").removeClass("graph-sub-link-selected");
        $(".graph-sub-link[href*='" + this.baseGraphHref(href) + "'][href*='" + sDtStart + "']").addClass("graph-sub-link-selected");
    },

    // called whenever user clicks graph type accordion
    loadGraphFromLink: function(el) {
        if (!el) return;
        Profile.loadGraphStudentListAware(el.href);
    },

    loadGraphStudentListAware: function(url) {
        var $dropdown = $('#studentlists_dropdown ol');
        if ($dropdown.length == 1) {
            var list_id = $dropdown.data('selected').key;
            var qs = this.parseQueryString(url);
            qs['list_id'] = list_id;
            qs['version'] = Profile.version;
            qs['dt'] = $("#targetDatepicker").val();
            url = this.baseGraphHref(url) + '?' + this.reconstructQueryString(qs);
        }
        
        this.loadGraph(url);
    },

    loadGraph: function(href, fNoHistoryEntry) {
        if (!href) return;

        if (this.fLoadingGraph) {
            setTimeout(function(){Profile.loadGraph(href);}, 200);
            return;
        }

        this.styleSublinkFromHref(href);
        this.fLoadingGraph = true;
        this.fLoadedGraph = true;

        var apiCallback = null;
        if (href.indexOf('/api/v1/user/exercises') > -1) {
			apiCallback = this.renderExercisesTable;
        }

        $.ajax({
			type: "GET",
			url: Timezone.append_tz_offset_query_param(href),
			data: {},
			dataType: apiCallback ? 'json' : 'html',
			success: function(data){
				Profile.finishLoadGraph(data, href, fNoHistoryEntry, apiCallback);
			},
			error: function() {
				Profile.finishLoadGraphError();
			}
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },

    finishLoadGraph: function(data, href, fNoHistoryEntry, apiCallback) {

        this.fLoadingGraph = false;

        if (!fNoHistoryEntry) {
            // Add history entry for browser
            if ($.address) {
                $.address.parameter("graph_url", encodeURIComponent(href), false);
			}
        }

        this.showGraphThrobber(false);
        this.styleSublinkFromHref(href);

        if (apiCallback) {
            apiCallback(data);
        } else {
            $("#graph-content").html(data);
        }
    },

    finishLoadGraphError: function() {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);
        $("#graph-content").html("<div class='graph-notification'>It's our fault. We ran into a problem loading this graph. Try again later, and if this continues to happen please <a href='/reportissue?type=Defect'>let us know</a>.</div>");
    },

	/**
	 * Renders the exercise blocks given the JSON blob about the exercises.
	 */
	renderExercisesTable: function(data) {
		// TODO: use a proper client side templating solution.
		var html = [];
		html.push( "<div id=\"module-progress\">" );
		for ( var i = 0, exercise; exercise = data[i]; i++ ) {
			var model = exercise["exercise_model"];
			var displayName = model["display_name"];
			var shortName = model["short_display_name"] || displayName;
			var stat = "Not started";
			var color = "";
			var states = exercise["exercise_states"];
			var progressStr = Math.floor( exercise["progress"] * 100 ) + "%";
			var totalDone = exercise["total_done"];

			if ( states["reviewing"] ) {
				stat = "Review";
				color = "review light";
			} else if ( states["proficient"] ) {
				// TODO: handle implicit proficiency - is that data in the API?
				// (due to proficiency in a more advanced module)
				stat = "Proficient";
				color = "proficient";
			} else if ( states["struggling"] ) {
				stat = "Struggling";
				color = "struggling";
			} else if ( totalDone > 0 ) {
				stat = "Started";
				color = "started";
			}

			if ( color ) {
				color = color + " action-gradient seethrough";
			} else {
				color = "transparent";
			}

			html.push(
					"<div class=\"student-module-status ",
						"exercise-progress-block exercise-color ", color, "\" ",
						"id=\"exercise-", model["name"], "\">",
					"<span class=\"exercise-display-name\"><nobr>",
					shortName,
					"</nobr></span>",
					"<div class=\"hover-data\" style=\"display: none;\">",
						"<div class=\"exercise-display-name\">",
							displayName, "</div>",
						"<div class=\"exercise-status\">Status: ",
							stat, "</div>",
						"<div class=\"exercise-progress\">Progress: ",
							progressStr, "</div>",
						"<div class=\"exercise-done\">Problems attempted: ",
							totalDone, "</div>",
					"</div>",
					"</div>");
		}
		html.push("<div style=\"clear:both\"></div></div>");
        $("#graph-content").html( html.join("") );

		var infoHover = $("#info-hover-container");
		var lastHoverTime;
		var mouseX;
		var mouseY;
		$("#module-progress .student-module-status").hover( 
			function(e) {
				var hoverTime = lastHoverTime = Date.now();
				mouseX = e.pageX;
				mouseY = e.pageY;
				var self = this;
				setTimeout(function() {
					if (hoverTime != lastHoverTime) {
						return;
					}

					var hoverData = $(self).children(".hover-data");
					if ($.trim(hoverData.html())) {
						infoHover.html($.trim(hoverData.html()));

						var left = mouseX + 15;
						var jelGraph = $("#graph-content");
						var leftMax = jelGraph.offset().left +
								jelGraph.width() - 150;

						infoHover.css('left', Math.min(left, leftMax));
						infoHover.css('top', mouseY + 5);
						infoHover.css('cursor', 'pointer');
						infoHover.show();
					}
				}, 100);
			},
			function(e){ 
				lastHoverTime = null;
				$("#info-hover-container").hide();
			}
		);
		$("#module-progress .student-module-status").click(function(e) {
			$("#info-hover-container").hide();
			Profile.collapseAccordion();
			// Extract the name from the ID, which has been prefixed.
			var exerciseName = this.id.substring( "exercise-".length );
			Profile.loadGraph(
				"/profile/graph/exerciseproblems?" +
				"exercise_name=" + exerciseName + "&" +
				"student_email=" + encodeURIComponent(Profile.email));
		});
	},

	// TODO: move history management out to a common utility
	historyChange: function(e) {
		var href = ( $.address ? $.address.parameter("graph_url") : "" ) ||
				this.initialGraphUrl;
		if ( href ) {
			href = decodeURIComponent( href );
			if ( this.expandAccordionForHref(href) ) {
				this.loadGraph( href, true );
			} else {
				// Invalid URL - just try the first link available.
				var links = $(".graph-link");
				if ( links.length ) {
					Profile.loadGraphFromLink( links[0] );
				}
			}
		}
	},

    showGraphThrobber: function(fVisible) {
        if (fVisible)
            $("#graph-progress-bar").progressbar({value: 100}).slideDown("fast");
        else
            $("#graph-progress-bar").slideUp("fast");
    },

	// TODO: move this out to a more generic utility file.
    parseQueryString: function(url) {
        var qs = {};
        var parts = url.split('?');
        if(parts.length == 2) {
            var querystring = parts[1].split('&');
            for(var i = 0; i<querystring.length; i++) {
                var kv = querystring[i].split('=');
                if(kv[0].length > 0) //fix trailing &
                    qs[kv[0]] = kv[1];
            }
        }
        return qs;
    },

	// TODO: move this out to a more generic utility file.
    reconstructQueryString: function(hash, kvjoin, eljoin) {
        kvjoin = kvjoin || '=';
        eljoin = eljoin || '&';
        qs = [];
        for(var key in hash) {
            if(hash.hasOwnProperty(key))
                qs.push(key + kvjoin + hash[key]);
        }
        return qs.join(eljoin);
    }
};

$(function(){Profile.init();});
