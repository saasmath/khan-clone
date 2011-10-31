
var Profile = {

    initialGraphUrl: null,
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
		if ( $.browser.msie && (parseInt($.browser.version, 10) < 8) )
			$(this).next(".sharepop").toggle();
		else
			$(this).next(".sharepop").toggle("drop",{direction:'up'},"fast");
		return false;
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

    expandAccordionForHref: function(href) {
        if (!href) return;

        href = this.baseGraphHref(href);

        href = href.replace(/[<>']/g, "");
        var selectorAccordionSection = ".graph-link-header[href*='" + href + "']";
        if ($(selectorAccordionSection).length)
            $("#stats-nav #nav-accordion").accordion("activate", selectorAccordionSection);
        else
            this.collapseAccordion();
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
            url = this.baseGraphHref(url) + '?' + this.reconstructQueryString(qs);
        }

        this.loadGraph(url);
    },

    loadGraph: function(href, fNoHistoryEntry) {
        var apiCallback = null;

        if (!href) return;

        if (this.fLoadingGraph) {
            setTimeout(function(){Profile.loadGraph(href);}, 200);
            return;
        }

        this.styleSublinkFromHref(href);
        this.fLoadingGraph = true;
        this.fLoadedGraph = true;

        if (href.indexOf('/api/v1/user/goals') > -1) {
            apiCallback = this.renderUserGoals;
        } else if (href.indexOf('/api/v1/user/students/goals') > -1) {
            apiCallback = this.renderStudentGoals;
        }

        $.ajax({type: "GET",
                url: Timezone.append_tz_offset_query_param(href),
                data: {},
                dataType: apiCallback ? 'json' : 'html',
                success: function(data){ Profile.finishLoadGraph(data, href, fNoHistoryEntry, apiCallback); },
                error: function() { Profile.finishLoadGraphError(); }
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },

    finishLoadGraph: function(data, href, fNoHistoryEntry, apiCallback) {

        this.fLoadingGraph = false;

        if (!fNoHistoryEntry)
        {
            // Add history entry for browser
            if ($.address)
                $.address.parameter("graph_url", encodeURIComponent(href), false);
        }

        this.showGraphThrobber(false);
        this.styleSublinkFromHref(href);

        if (apiCallback) {
            apiCallback(data);
        } else {
            $("#graph-content").html(data);
        }
    },

    renderUserGoals: function(data) {
        $("#graph-content").html($('#goals-all-tmpl').tmplPlugin({'goals':data}));
    },
    renderStudentGoals: function(data) {
        var goal_list = []

        $.each(data, function(idx1, student) {
            student.goal_count = 0;
            student.most_recent_update = null;

            if (student.goals != undefined) {
                $.each(student.goals, function(idx2, goal) {
                    // Sort objectives by status
                    var statuses = ['started','struggling','proficient'];
                    var progress_count = 0;
                    goal.objectives.sort(function(a,b) { return statuses.indexOf(b.status)-statuses.indexOf(a.status); });
                    $.each(goal.objectives, function(idx3, objective) {
                        if (objective.status == 'proficient')
                            progress_count += 1000;
                        else if (objective.status == 'started' || objective.status == 'struggling')
                            progress_count += 1;
                    });

                    if (!student.most_recent_update || goal.updated > student.most_recent_update)
                        student.most_recent_update = goal;

                    student.goal_count++;
                    goal_list.push({
                        student: student,
                        goal: goal,
                        progress_count: progress_count,
                        goal_idx: student.goal_count,
                        visible: true,
                        show_counts: true,
                    });
                });
            } else {
                goal_list.push({student:student,progress_count:-1});
            }
        });
        
        Profile.updateStudentGoals(goal_list);

        $("#student-goals-sort").change(function() { Profile.updateStudentGoals(goal_list) });
        $("input[name=\"student-goals-filter\"]").change(function() { Profile.updateStudentGoals(goal_list) });
    },
    updateStudentGoals: function(goal_list) {
        var sort = $("#student-goals-sort").val();
        var filter = 'all';
        if ($('#student-goals-filter-most-recent').is(":checked"))
            filter = 'most-recent';
        if ($('#student-goals-filter-in-progress').is(":checked"))
            filter = 'in-progress';

        if (sort == 'name') {
            goal_list.sort(function(a,b) {
                if (b.student.nickname > a.student.nickname)
                    return -1;
                if (b.student.nickname < a.student.nickname)
                    return 1;
                return a.goal_idx-b.goal_idx;
            });
        } else if (sort == 'progress') {
            goal_list.sort(function(a,b) { return b.progress_count - a.progress_count; });
        } else if (sort == 'created') {
            goal_list.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.created > a.goal.created)
                        return -1;
                    if (b.goal.created < a.goal.created)
                        return 1;
                }
                return 0;
            });
        } else if (sort == 'updated') {
            goal_list.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.updated > a.goal.updated)
                        return 1;
                    if (b.goal.updated < a.goal.updated)
                        return -1;
                }
                return 0;
            });
        }

        $.each(goal_list, function(idx, row) {
            if (filter == 'most-recent') {
                row.visible = !row.goal || (row.goal == row.student.most_recent_update);
            } else if (filter == 'in-progress') {
                row.visible = row.goal && (row.progress_count > 0);
            } else {
                row.visible = true;
            }
            row.show_counts = !(filter == 'most-recent');
        });
        
        $("#graph-content").html($('#profile-student-goals-tmpl').tmplPlugin({'goal_list':goal_list}));

        $("#student-goals-sort").val(sort);
        $("#student-goals-sort").change(function() { Profile.updateStudentGoals(goal_list) });

        $('#student-goals-filter-'+filter).prop("checked", true);
        $("input[name=\"student-goals-filter\"]").change(function() { Profile.updateStudentGoals(goal_list) });
    },

    finishLoadGraphError: function() {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);
        $("#graph-content").html("<div class='graph-notification'>It's our fault. We ran into a problem loading this graph. Try again later, and if this continues to happen please <a href='/reportissue?type=Defect'>let us know</a>.</div>");
    },

    historyChange: function(e) {
        var href = ($.address ? $.address.parameter("graph_url") : "") || this.initialGraphUrl;
        href = decodeURIComponent(href);
        if (href)
        {
            this.expandAccordionForHref(href);
            this.loadGraph(href, true);
        }
    },

    showGraphThrobber: function(fVisible) {
        if (fVisible)
            $("#graph-progress-bar").progressbar({value: 100}).slideDown("fast");
        else
            $("#graph-progress-bar").slideUp("fast");
    },

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
