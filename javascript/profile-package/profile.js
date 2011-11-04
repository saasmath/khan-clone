
var Profile = {

    version: 0,
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

        ko.bindingHandlers.throbberLeft = {
            update: function(element, valueAccessor) {
                var visible = valueAccessor()();
                if (visible)
                    Throbber.show($(element), true);
                else
                    Throbber.hide();
            },
        };
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
            qs['version']=Profile.version;
            qs['dt'] = $("#targetDatepicker").val();
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
            apiCallback(data, href);
        } else {
            $("#graph-content").html(data);
        }
    },

    renderUserGoals: function(data, href) {
        var goals_model = {
            'current_goals': ko.observableArray([]),
            'completed_goals': ko.observableArray([]),
            'abandoned_goals': ko.observableArray([]),
        };
        $.each(data, function(idx, goal) {
            goal.progress = totalProgress(goal.objectives).toFixed(0);
            if (goal.completed != undefined) {
                if (goal.abandoned)
                    goals_model.abandoned_goals.push(goal);
                else
                    goals_model.completed_goals.push(goal);
            } else {
                goals_model.current_goals.push(goal);
            }

            goal.abandon_inprogress = ko.observable(false);
            goal.abandon = function() {
                if (confirm("This action cannot be undone. Abandon goal?")) {
                    goal.abandon_inprogress(true);
                    $.ajax({
                        url: "/api/v1/user/goals/abandon/" + goal.id,
                        type: 'POST',
                        dataType: 'json',
                        success: function(json) {
                            goal.abandon_inprogress(false);

                            $.each(Goals.all, function(idx, other_goal) {
                                if (goal.id == other_goal.id) {
                                    Goals.all.splice(idx, 1);
                                    return false;
                                }
                            });
                            updateGoals(Goals.all);
                            Profile.loadGraph(href);
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            goal.abandon_inprogress(false);
                        },
                    });
                }
            };
        });
        $("#graph-content").html($('#profile-goals-tmpl').tmplPlugin({'goals':data}));
        ko.applyBindings(goals_model, $("#student-goals").get(0));
    },

    renderStudentGoals: function(data, href) {
        var goals_model = {
            'sort_desc': ko.observable(''),
            'filter_desc': ko.observable(''),
            'row_data': ko.observableArray([]),
        }; 

        $.each(data, function(idx1, student) {
            student.goal_count = 0;
            student.most_recent_update = null;
            student.profile_url = "/profile?k&student_email="+student.email+"#/?graph_url=/api/v1/user/goals%3Fstudent_email="+student.email;

            if (student.goals != undefined && student.goals.length > 0) {
                $.each(student.goals, function(idx2, goal) {
                    // Sort objectives by status
                    var statuses = ['started','struggling','proficient'];
                    var progress_count = 0;
                    var found_struggling = false;

                    goal.objectives.sort(function(a,b) { return statuses.indexOf(b.status)-statuses.indexOf(a.status); });

                    $.each(goal.objectives, function(idx3, objective) {
                        if (objective.status == 'proficient')
                            progress_count += 1000;
                        else if (objective.status == 'started' || objective.status == 'struggling')
                            progress_count += 1;
                        if (objective.status == 'struggling')
                            found_struggling = true;

                        objective.filter_match = ko.observable(true);

                        if (objective.type == 'GoalObjectiveExerciseProficiency') {
                            objective.click_fn = function() {
                                Profile.collapseAccordion();
                                Profile.loadGraph('/profile/graph/exerciseproblems?student_email='+student.email+'&exercise_name='+objective.internal_id);
                            };
                        } else {
                            // TomY TODO Do something here for videos?
                            objective.click_fn = function() { };
                        }
                    });

                    if (!student.most_recent_update || goal.updated > student.most_recent_update)
                        student.most_recent_update = goal;

                    student.goal_count++;
                    goals_model.row_data.push({
                        student: student,
                        goal: goal,
                        progress_count: progress_count,
                        goal_idx: student.goal_count,
                        visible: ko.observable(true),
                        show_counts: ko.observable(true),
                        struggling: found_struggling,
                    });
                });
            } else {
                goals_model.row_data.push({
                    student: student,
                    goal: { objectives:[] },
                    progress_count: -1,
                    goal_idx: 0,
                    visible: ko.observable(true),
                    show_counts: ko.observable(false),
                    struggling: false,
                });
            }
        });

        $("#graph-content").html($('#profile-student-goals-tmpl').html());

        ko.bindingHandlers.student_objective_css = {
            update: function(element, valueAccessor) {
                var objective = ko.utils.unwrapObservable(valueAccessor())
                $(element).addClass(objective.status);
                $(element).addClass(objective.type);
            },
        };
        ko.applyBindings(goals_model, $("#class-student-goals").get(0));

        $("#student-goals-sort").change(function() { Profile.sortStudentGoals(goals_model) });

        $("input.student-goals-filter-check").change(function() { Profile.filterStudentGoals(goals_model) });
        $("#student-goals-search").keyup(function() { Profile.filterStudentGoals(goals_model) });
        
        Profile.sortStudentGoals(goals_model);
        Profile.filterStudentGoals(goals_model);
    },
    sortStudentGoals: function(goals_model) {
        var sort = $("#student-goals-sort").val();
        var rows = $("#class-student-goal").children().get();

        if (sort == 'name') {
            rows.sort(function(a,b) {
                a_data = ko.dataFor(a);
                b_data = ko.dataFor(b);
                if (b_data.student.nickname > a_data.student.nickname)
                    return -1;
                if (b_data.student.nickname < a_data.student.nickname)
                    return 1;
                return a_data.goal_idx-b_data.goal_idx;
            });

            goals_model.sort_desc('student name');
            
        } else if (sort == 'progress') {
            rows.sort(function(a,b) {
                a_data = ko.dataFor(a);
                b_data = ko.dataFor(b);
                return b_data.progress_count - a_data.progress_count;
            });

            goals_model.sort_desc('goal progress');

        } else if (sort == 'created') {
            rows.sort(function(a,b) {
                a_data = ko.dataFor(a);
                b_data = ko.dataFor(b);
                if (a_data.goal && !b_data.goal)
                    return -1;
                if (b_data.goal && !a_data.goal)
                    return 1;
                if (a_data.goal && b_data.goal) {
                    if (b_data.goal.created > a_data.goal.created)
                        return 1;
                    if (b_data.goal.created < a_data.goal.created)
                        return -1;
                }
                return 0;
            });

            goals_model.sort_desc('goal creation time');

        } else if (sort == 'updated') {
            rows.sort(function(a,b) {
                a_data = ko.dataFor(a);
                b_data = ko.dataFor(b);
                if (a_data.goal && !b_data.goal)
                    return -1;
                if (b_data.goal && !a_data.goal)
                    return 1;
                if (a_data.goal && b_data.goal) {
                    if (b_data.goal.updated > a_data.goal.updated)
                        return 1;
                    if (b_data.goal.updated < a_data.goal.updated)
                        return -1;
                }
                return 0;
            });

            goals_model.sort_desc('last work logged time');
        }

        $.each(rows, function(idx, element) { $("#class-student-goal").append(element); });
    },
    filterStudentGoals: function(goals_model) {
        var filter_text = $.trim($("#student-goals-search").val().toLowerCase());
        var filters = {};
        $("input.student-goals-filter-check").each(function(idx, element) {
            filters[$(element).attr('name')] = $(element).is(":checked");
        });

        var filters_desc = '';
        if (filters['most-recent']) {
            filters_desc += 'most recently worked on goals';
        }
        if (filters['active']) {
            if (filters_desc != '') filters_desc += ', ';
            filters_desc += 'active goals';
        }
        if (filters['in-progress']) {
            if (filters_desc != '') filters_desc += ', ';
            filters_desc += 'goals in progress';
        }
        if (filters['struggling']) {
            if (filters_desc != '') filters_desc += ', ';
            filters_desc += 'students who are struggling';
        }
        if (filter_text != '') {
            if (filters_desc != '') filters_desc += ', ';
            filters_desc += 'students/goals matching "' + filter_text + '"';
        }
        if (filters_desc != '')
            goals_model.filter_desc('Showing only ' + filters_desc);
        else
            goals_model.filter_desc('No filters applied');

        $.each(goals_model.row_data(), function(idx, row) {
            var row_visible = true;
            if (filters['most-recent']) {
                row_visible = row_visible && (!row.goal || (row.goal == row.student.most_recent_update));
            }
            if (filters['in-progress']) {
                row_visible = row_visible && (row.goal && (row.progress_count > 0));
            } 
            if (filters['active']) {
                row_visible = row_visible && (row.goal && row.goal.active);
            } 
            if (filters['struggling']) {
                row_visible = row_visible && (row.struggling);
            } 

            if (row_visible) {
                if (filter_text == '') {
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx2, objective) {
                            objective.filter_match(true);
                        });
                    }
                } else {
                    if (row.student.nickname.toLowerCase().indexOf(filter_text) >= 0) {
                        if (row.goal) {
                            $.each(row.goal.objectives, function(idx2, objective) {
                                objective.filter_match(true);
                            });
                        }
                    } else {
                        row_visible = false;
                        if (row.goal) {
                            $.each(row.goal.objectives, function(idx2, objective) {
                                if (objective.description.toLowerCase().indexOf(filter_text) >= 0) {
                                    objective.filter_match(true);
                                    row_visible = true;
                                } else {
                                    objective.filter_match(false);
                                }
                            });
                        }
                    }
                }
            }
            row.visible(row_visible);
            row.show_counts(!filters['most-recent'] && !filters['active']);
        });
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
