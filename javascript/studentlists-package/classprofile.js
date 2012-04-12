/**
 * Code to handle the logic for the class profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

var ClassProfile = {
    version: 0,
    initialGraphUrl: null, // Filled in by the template after script load.
    fLoadingGraph: false,
    fLoadedGraph: false,

    init: function() {
        // Init Highcharts global options.
        Highcharts.setOptions({
            credits: {
                enabled: false
            },
            title: {
                text: ""
            },
            subtitle: {
                text: ""
            }
        });

        if ($.address){

            // this is hackish, but it prevents the change event from being fired twice on load
            if ( $.address.value() === "/" ){
                window.location = window.location + "#" + $(".graph-link:eq(0)").attr("href");
            }

            $.address.change(function( evt ){

                if ( $.address.path() !== "/"){
                    ClassProfile.historyChange( evt );
                }

            });

        }

        $(".graph-link").click(
            function(evt){
                evt.preventDefault();
                if($.address){
                    // only visit the resource described by the url, leave the params unchanged
                    var href = $( this ).attr( "href" )
                    var path = href.split("?")[0];

                    // visiting a different resource
                    if ( path !== $.address.path() ){
                        $.address.path( path );
                    }

                    // applying filters for same resource via querystring
                    else{
                        // make a dict of current qs params and merge with the link's
                        var currentParams = {};
                        _.map( $.address.parameterNames(), function(e){ currentParams[e] = $.address.parameter( e ); } );
                        var linkParams = ClassProfile.parseQueryString( href );
                        $.extend( currentParams, linkParams );

                        $.address.queryString( ClassProfile.reconstructQueryString( currentParams ) );
                    }
                }
            }
        );

        // remove goals from IE<=8
        $(".lte8 .goals-accordion-content").remove();

        $("#stats-nav #nav-accordion")
            .accordion({
                header:".header",
                active:".graph-link-selected",
                autoHeight: false,
                clearStyle: true
            });

        setTimeout(function(){
            if (!ClassProfile.fLoadingGraph && !ClassProfile.fLoadedGraph)
            {
                // If 1000 millis after document.ready fires we still haven't
                // started loading a graph, load manually.
                // The externalChange trigger may have fired before we hooked
                // up a listener.
                ClassProfile.historyChange();
            }
        }, 1000);

        ClassProfile.ProgressSummaryView = new ProgressSummaryView();

        $('#studentlists_dropdown').css('display', 'inline-block');
        var $dropdown = $('#studentlists_dropdown ol');
        if ($dropdown.length > 0) {
            var menu = $dropdown.menu();

            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css('position', 'absolute');

            menu.bind("menuselect", this.updateStudentList);

            $(document).bind("click focusin", function(e){
                if ($(e.target).closest("#studentlists_dropdown").length == 0) {
                    menu.hide();
                }
            });

            var button = $('#studentlists_dropdown > a').button({
                icons: {
                    secondary: 'ui-icon-triangle-1-s'
                }
            }).show().click(function(e){
                if (menu.css('display') == 'none')
                    menu.show().menu("activate", e, $('#studentlists_dropdown li[data-selected=selected]')).focus();
                else
                    menu.hide();
                e.preventDefault();
            });

            // get initially selected list
            var list_id = $dropdown.children('li[data-selected=selected]').data('list_id');
            var student_list = ClassProfile.getStudentListFromId(list_id);
            $dropdown.data('selected', student_list);
        }
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

        href = this.baseGraphHref(href).replace(/[<>']/g, "");

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
        $(".graph-sub-link[href*='" + this.baseGraphHref(href) + "'][href*='" + sDtStart + "']")
            .addClass("graph-sub-link-selected");
    },

    // called whenever user clicks graph type accordion
    loadGraphFromLink: function(el) {
        if (!el) return;
        ClassProfile.loadGraphStudentListAware(el.href);
    },

    loadGraphStudentListAware: function(url) {
        var $dropdown = $('#studentlists_dropdown ol');
        if ($dropdown.length == 1) {
            var list_id = $dropdown.data('selected').key;
            var qs = this.parseQueryString(url);
            qs['list_id'] = list_id;
            qs['version'] = ClassProfile.version;
            qs['dt'] = $("#targetDatepicker").val();
            url = this.baseGraphHref(url) + '?' + this.reconstructQueryString(qs);
        }

        this.loadGraph(url);
    },

    loadFilters : function( href ){
        // fix the hrefs for each filter
        var a = $("#stats-filters a[href^=\"" + href + "\"]").parent();
        $("#stats-filters .filter:visible").not(a).slideUp("slow");
        a.slideDown();
    },

    loadGraph: function(href, fNoHistoryEntry) {
        var apiCallbacksTable = {
            '/api/v1/user/students/goals': this.renderStudentGoals,
            '/api/v1/user/students/progressreport': ClassProfile.renderStudentProgressReport,
            '/api/v1/user/students/progress/summary': this.ProgressSummaryView.render
        };
        if (!href) return;

        if (this.fLoadingGraph) {
            setTimeout(function(){ClassProfile.loadGraph(href);}, 200);
            return;
        }

        this.styleSublinkFromHref(href);
        this.fLoadingGraph = true;
        this.fLoadedGraph = true;

        var apiCallback = null;
        for (var uri in apiCallbacksTable) {
            if (href.indexOf(uri) > -1) {
                apiCallback = apiCallbacksTable[uri];
            }
        }
        $.ajax({
            type: "GET",
            url: Timezone.append_tz_offset_query_param(href),
            data: {},
            dataType: apiCallback ? 'json' : 'html',
            success: function(data){
                ClassProfile.finishLoadGraph(data, href, fNoHistoryEntry, apiCallback);
            },
            error: function() {
                ClassProfile.finishLoadGraphError();
            }
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },
    renderStudentGoals: function(data, href) {
        var studentGoalsViewModel = {
            rowData: [],
            sortDesc: '',
            filterDesc: '',
            colors: "goals-class"
        };

        $.each(data, function(idx1, student) {
            student.goal_count = 0;
            student.most_recent_update = null;
            student.profile_url = student.profile_root + "goals";

            if (student.goals != undefined && student.goals.length > 0) {
                $.each(student.goals, function(idx2, goal) {
                    // Sort objectives by status
                    var progress_count = 0;
                    var found_struggling = false;

                    goal.objectiveWidth = 100/goal.objectives.length;
                    goal.objectives.sort(function(a,b) { return b.progress-a.progress; });

                    $.each(goal.objectives, function(idx3, objective) {
                        Goal.calcObjectiveDependents(objective, goal.objectiveWidth);

                        if (objective.status == 'proficient')
                            progress_count += 1000;
                        else if (objective.status == 'started' || objective.status == 'struggling')
                            progress_count += 1;

                        if (objective.status == 'struggling') {
                            found_struggling = true;
                            objective.struggling = true;
                        }
                        objective.statusCSS = objective.status ? objective.status : "not-started";
                        objective.objectiveID = idx3;
                        var base = student.profile_root + "vital-statistics";
                        if (objective.type === "GoalObjectiveExerciseProficiency") {
                            objective.url = base + "/problems/" + objective.internal_id;
                        } else if (objective.type === "GoalObjectiveAnyExerciseProficiency") {
                            objective.url = base + "/skill-progress";
                        } else {
                            objective.url = base + "/activity";
                        }
                    });

                    // normalize so completed goals sort correctly
                    if (goal.objectives.length) {
                        progress_count /= goal.objectives.length;
                    }

                    if (!student.most_recent_update || goal.updated > student.most_recent_update)
                        student.most_recent_update = goal;

                    student.goal_count++;
                    row = {
                        rowID: studentGoalsViewModel.rowData.length,
                        student: student,
                        goal: goal,
                        progress_count: progress_count,
                        goal_idx: student.goal_count,
                        struggling: found_struggling
                    };

                    $.each(goal.objectives, function(idx3, objective) {
                        objective.row = row;
                    });
                    studentGoalsViewModel.rowData.push(row);
                });
            } else {
                studentGoalsViewModel.rowData.push({
                    rowID: studentGoalsViewModel.rowData.length,
                    student: student,
                    goal: {objectives: []},
                    progress_count: -1,
                    goal_idx: 0,
                    struggling: false
                });
            }
        });

        var template = Templates.get( "profile.profile-class-goals" );
        $("#graph-content").html( template(studentGoalsViewModel) );

        $("#class-student-goal .goal-row").each(function() {
            var goalViewModel = studentGoalsViewModel.rowData[$(this).attr('data-id')];
            goalViewModel.rowElement = this;
            goalViewModel.countElement = $(this).find('.goal-count');
            goalViewModel.startTimeElement = $(this).find('.goal-start-time');
            goalViewModel.updateTimeElement = $(this).find('.goal-update-time');

            Profile.hoverContent($(this).find(".objective"));

            $(this).find("a.objective").each(function() {
                var goalObjective = goalViewModel.goal.objectives[$(this).attr('data-id')];
                goalObjective.blockElement = this;

                if (goalObjective.type == 'GoalObjectiveExerciseProficiency') {
                    $(this).click(function() {
                        // TODO: awkward turtle, replace with normal href action
                        window.location = goalViewModel.student.profile_root
                                            + "/vital-statistics/problems/"
                                            + goalObjective.internal_id;
                    });
                } else {
                    // Do something here for videos?
                }
            });
        });

        $("#student-goals-sort")
            .off("change.goalsfilter")
            .on("change.goalsfilter", function() {
                ClassProfile.sortStudentGoals(studentGoalsViewModel);
            });
        $("input.student-goals-filter-check")
            .off("change.goalsfilter")
            .on("change.goalsfilter", function() {
                ClassProfile.filterStudentGoals(studentGoalsViewModel);
            });
        $("#student-goals-search")
            .off("keyup.goalsfilter")
            .on("keyup.goalsfilter", function() {
                ClassProfile.filterStudentGoals(studentGoalsViewModel);
            });

        ClassProfile.sortStudentGoals(studentGoalsViewModel);
        ClassProfile.filterStudentGoals(studentGoalsViewModel);
    },
    sortStudentGoals: function(studentGoalsViewModel) {
        var sort = $("#student-goals-sort").val();
        var show_updated = false;

        if (sort == 'name') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (b.student.nickname > a.student.nickname)
                    return -1;
                if (b.student.nickname < a.student.nickname)
                    return 1;
                return a.goal_idx-b.goal_idx;
            });

            studentGoalsViewModel.sortDesc = 'student name';
            show_updated = false; // started

        } else if (sort == 'progress') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                return b.progress_count - a.progress_count;
            });

            studentGoalsViewModel.sortDesc = 'goal progress';
            show_updated = true; // updated

        } else if (sort == 'created') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.created > a.goal.created)
                        return 1;
                    if (b.goal.created < a.goal.created)
                        return -1;
                }
                return 0;
            });

            studentGoalsViewModel.sortDesc = 'goal creation time';
            show_updated = false; // started

        } else if (sort == 'updated') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
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

            studentGoalsViewModel.sortDesc = 'last work logged time';
            show_updated = true; // updated
        }

        var container = $('#class-student-goal').detach();
        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            $(row.rowElement).detach();
            $(row.rowElement).appendTo(container);
            if (show_updated) {
                row.startTimeElement.hide();
                row.updateTimeElement.show();
            } else {
                row.startTimeElement.show();
                row.updateTimeElement.hide();
            }
        });
        container.insertAfter('#class-goal-filter-desc');

        ClassProfile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },
    updateStudentGoalsFilterText: function(studentGoalsViewModel) {
        var text = 'Sorted by ' + studentGoalsViewModel.sortDesc + '. ' + studentGoalsViewModel.filterDesc + '.';
        $('#class-goal-filter-desc').html(text);
    },
    filterStudentGoals: function(studentGoalsViewModel) {
        var filter_text = $.trim($("#student-goals-search").val().toLowerCase());
        var filters = {};
        $("input.student-goals-filter-check").each(function(idx, element) {
            filters[$(element).attr('name')] = $(element).is(":checked");
        });

        studentGoalsViewModel.filterDesc = '';
        if (filters['most-recent']) {
            studentGoalsViewModel.filterDesc += 'most recently worked on goals';
        }
        if (filters['in-progress']) {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'goals in progress';
        }
        if (filters['struggling']) {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'students who are struggling';
        }
        if (filter_text != '') {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'students/goals matching "' + filter_text + '"';
        }
        if (studentGoalsViewModel.filterDesc != '')
            studentGoalsViewModel.filterDesc = 'Showing only ' + studentGoalsViewModel.filterDesc;
        else
            studentGoalsViewModel.filterDesc = 'No filters applied';

        var container = $('#class-student-goal').detach();

        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            var row_visible = true;

            if (filters['most-recent']) {
                row_visible = row_visible && (!row.goal || (row.goal == row.student.most_recent_update));
            }
            if (filters['in-progress']) {
                row_visible = row_visible && (row.goal && (row.progress_count > 0));
            }
            if (filters['struggling']) {
                row_visible = row_visible && (row.struggling);
            }
            if (row_visible) {
                if (filter_text == '' || row.student.nickname.toLowerCase().indexOf(filter_text) >= 0) {
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            $(objective.blockElement).removeClass('matches-filter');
                        });
                    }
                } else {
                    row_visible = false;
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            if ((objective.description.toLowerCase().indexOf(filter_text) >= 0)) {
                                row_visible = true;
                                $(objective.blockElement).addClass('matches-filter');
                            } else {
                                $(objective.blockElement).removeClass('matches-filter');
                            }
                        });
                    }
                }
            }

            if (row_visible)
                $(row.rowElement).show();
            else
                $(row.rowElement).hide();

            if (filters['most-recent'])
                row.countElement.hide();
            else
                row.countElement.show();
        });

        container.insertAfter('#class-goal-filter-desc');

        ClassProfile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },
    finishLoadGraph: function(data, href, fNoHistoryEntry, apiCallback) {

        this.fLoadingGraph = false;

        if (!fNoHistoryEntry) {
            // Add history entry for browser
            //             if ($.address) {
            //                 $.address(href);
            // }
        }

        this.showGraphThrobber(false);
        this.styleSublinkFromHref(href);

        var start = (new Date).getTime();
        if (apiCallback) {
            apiCallback(data, href);
        } else {
            $("#graph-content").html(data);
        }
        var diff = (new Date).getTime() - start;
        KAConsole.log('API call rendered in ' + diff + ' ms.');
    },

    finishLoadGraphError: function() {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);
        $("#graph-content").html("<div class='graph-notification'>It's our fault. We ran into a problem loading this graph. Try again later, and if this continues to happen please <a href='/reportissue?type=Defect'>let us know</a>.</div>");
    },

    // TODO: move history management out to a common utility
    historyChange: function(e) {
        var href = ( $.address.value() === "/" ) ? this.initialGraphUrl : $.address.value();
        var url = ( $.address.path() === "/" ) ? this.initialGraphUrl : $.address.path();

        if ( href ) {
            if ( this.expandAccordionForHref(href) ) {
                this.loadGraph( href , true );
                this.loadFilters( url );
            } else {
                // Invalid URL - just try the first link available.
                var links = $(".graph-link");
                if ( links.length ) {
                    ClassProfile.loadGraphFromLink( links[0] );
                }
            }
        }
    },

    showGraphThrobber: function(fVisible) {
        if (fVisible) {
            $("#graph-progress-bar").progressbar({value: 100}).slideDown("fast");
        } else {
            $("#graph-progress-bar").slideUp("fast", function() {
                $(this).hide();
            });
        }
    },

    // TODO: move this out to a more generic utility file.
    parseQueryString: function(url) {
        var qs = {};
        var parts = url.split('?');
        if(parts.length == 2) {
            var querystring = parts[1].split('&');
            for(var i = 0; i<querystring.length; i++) {
                var kv = querystring[i].split('=');
                if(kv[0].length > 0) { //fix trailing &
                    key = decodeURIComponent(kv[0]);
                    value = decodeURIComponent(kv[1]);
                    qs[key] = value;
                }
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
    },

    getStudentListFromId: function (list_id) {
        var student_list;
        jQuery.each(this.studentLists, function(i,l) {
            if (l.key == list_id) {
                student_list = l;
                return false;
            }
        });
        return student_list;
    },

    // called whenever user selects student list dropdown
    updateStudentList: function(event, ui) {
        // change which item has the selected attribute
        // weird stuff happening with .data(), just use attr for now...
        var $dropdown = $('#studentlists_dropdown ol');
        $dropdown.children('li[data-selected=selected]').removeAttr('data-selected');
        $(ui.item).attr('data-selected', 'selected');

        // store which class list is selected
        var student_list = ClassProfile.getStudentListFromId(ui.item.data('list_id'));
        $dropdown.data('selected', student_list);

        // update the address parameter
        $.address.parameter("list_id",ui.item.data('list_id'))


        // update appearance of dropdown
        $('#studentlists_dropdown .ui-button-text').text(student_list.name);
        $dropdown.hide();

        $('#count_students').html('&hellip;');
        $('#energy-points .energy-points-badge').html('&hellip;');
    },

    updateStudentInfo: function(students, energyPoints) {
        $('#count_students').text(students + '');
        if ( typeof energyPoints !== "string" ) {
            energyPoints = addCommas(energyPoints);
        }
        $('#energy-points .energy-points-badge').text(energyPoints);
    },

    renderStudentProgressReport: function(data, href) {
        ClassProfile.updateStudentInfo(data.exercise_data.length, data.c_points);

        $.each(data.exercise_names, function(idx, exercise) {
            exercise.display_name_lower = exercise.display_name.toLowerCase();
            exercise.idx = idx;
        });

        data.exercise_list = [];
        $.each(data.exercise_data, function(idx, student_row) {
            data.exercise_list.push(student_row);
        });
        data.exercise_list.sort(function(a, b) { if (a.nickname < b.nickname) return -1; else if (b.nickname < a.nickname) return 1; return 0; });

        $.each(data.exercise_list, function(idx, student_row) {
            student_row.idx = idx;
            student_row.nickname_lower = student_row.nickname.toLowerCase();

            $.each(student_row.exercises, function(idx2, exercise) {
                exercise.exercise_display = data.exercise_names[idx2].display_name;
                exercise.progress = (exercise.progress*100).toFixed(0);
                // TODO: awkward turtle, replace w normal href
                exercise.link = student_row.profile_root
                                    + "/vital-statistics/problems/"
                                    + data.exercise_names[idx2].name;
                if (exercise.last_done) {
                    exercise.seconds_since_done = ((new Date()).getTime() - Date.parse(exercise.last_done)) / 1000;
                } else {
                    exercise.seconds_since_done = 1000000;
                }

                exercise.status_css = 'transparent';
                if (exercise.status == 'Review') exercise.status_css = 'review light';
                else if (exercise.status.indexOf('Proficient') == 0) exercise.status_css = 'proficient';
                else if (exercise.status == 'Struggling') exercise.status_css = 'struggling';
                else if (exercise.status == 'Started') exercise.status_css = 'started';
                exercise.notTransparent = (exercise.status_css != 'transparent');

                exercise.idx = idx2;
            });
        });

        var template = Templates.get( "profile.profile-class-progress-report" );

        $("#graph-content").html( template(data) );
        ProgressReport.init(data);
    }
};

var ProgressReport = {

    updateFilterTimeout: null,

    studentRowView: Backbone.View.extend({
        initialize: function() {
            this.columnViews = [];
        },

        updateFilter: function(visibleColumns) {
            if (this.model.visible) {
                if (this.model.highlight && this.options.allowHighlight) {
                    $(this.el).addClass('highlight');
                } else {
                    $(this.el).removeClass('highlight');
                }

                if (this.model.hiddenCount) {
                    $(this.el).find('.hidden-students').html('(' + this.model.hiddenCount + ' hidden)');
                }

                $(this.el).show();

                $.each(this.columnViews, function(idx, columnView) {
                    columnView.updateFilter(visibleColumns, null, this.model.matchingCells);
                });
            } else {
                $(this.el).hide();
            }
        }
    }),
    studentColumnView: Backbone.View.extend({
        updateFilter: function(visibleColumns, matchingColumns, matchingCells) {
            if (visibleColumns[this.options.index]) {
                if (matchingColumns && matchingColumns[this.options.index]) {
                    $(this.el).addClass('highlight');
                } else {
                    $(this.el).removeClass('highlight');
                }

                if (matchingCells && !matchingCells[this.options.index]) {
                    $(this.el).addClass('notmatching');
                } else {
                    $(this.el).removeClass('notmatching');
                }

                $(this.el).show();
            } else {
                $(this.el).hide();
            }
        }
    }),

    init: function(model) {
        var self = this;

        this.model = model;
        this.rowViews = [];
        this.headingViews = [];
        this.hiddenStudentsModel = {
            'visible': false,
            'highlight': false,
            'hiddenCount': 10
        };

        if ($.browser.msie && parseInt($.browser.version) < 8) {
            this.showBrowserRequirements();
            return;
        }

        var adjustData = this.preAdjustTable();
        temporaryDetachElement($('#module-progress'), function() {
            this.adjustTable(adjustData);
        }, this);

        this.onResize();
        $("#module-progress td.student-module-status").hover(this.onHover, this.onUnhover);

        if (!window.fBoundProgressReport) {
            $(window).resize(ProgressReport.onResize);
            $(document).mousemove(function(e){window.mouseX = e.pageX; window.mouseY = e.pageY;});
            window.fBoundProgressReport = true;
        }

        $('#module-progress').find('th.student-exercises-col').each(function() {
            var col_idx = $(this).attr('data-id');
            self.headingViews.push(new ProgressReport.studentColumnView({
                el: this,
                model: null,
                index: col_idx
            }));
        });
        $('#module-progress').find('tr.student-email-row').each(function() {
            var row_idx = $(this).attr('data-id');
            var row = (row_idx >= 0) ? model.exercise_list[row_idx] : self.hiddenStudentsModel;
            self.rowViews.push(new ProgressReport.studentRowView({
                el: this,
                model: row,
                allowHighlight: true
            }));
        });
        $('#module-progress').find('tr.student-exercises-row').each(function() {
            var row_idx = $(this).attr('data-id');
            var row = (row_idx >= 0) ? model.exercise_list[row_idx] : self.hiddenStudentsModel;

            var rowView = new ProgressReport.studentRowView({
                el: this,
                model: row
            });
            self.rowViews.push(rowView);

            $(this).find('td.student-module-status').each(function() {
                var col_idx = $(this).attr('data-id');
                rowView.columnViews.push(new ProgressReport.studentColumnView({
                    el: this,
                    model: row,
                    index: col_idx
                }));
                $(this).click(function() {
                    // TODO: awkward turtle this should really just be a link,
                    // but I don't feel like combing through right now.
                    window.location = row.exercises[col_idx].link;
                });
            });
        });

        $("#student-progressreport-search").unbind();
        $("#student-progressreport-search").keyup(function() {
            if (ProgressReport.updateFilterTimeout == null) {
                ProgressReport.updateFilterTimeout = setTimeout(function() {
                    ProgressReport.filterRows(model);
                    ProgressReport.updateFilterTimeout = null;
                }, 250);
            }
        });

        $("input.progressreport-filter-check").unbind();
        $("input.progressreport-filter-check").change(function() { ProgressReport.filterRows(model); });
        $("#progressreport-filter-last-time").change(function() {
            $("input.progressreport-filter-check[name=\"recent\"]").attr("checked", true);
            ProgressReport.filterRows(model);
        });

        ProgressReport.filterRows(model);
    },

    filterRows: function(model) {
        var filterText = $.trim($('#student-progressreport-search').val().toLowerCase());
        var filters = {};
        $("input.progressreport-filter-check").each(function(idx, element) {
            filters[$(element).attr('name')] = $(element).is(":checked");
        });
        var filterRecentTime = $("#progressreport-filter-last-time").val();

        var visibleColumns = [];
        var matchingColumns = [];
        var hiddenCount = 0;

        // Match columns with filter text
        $.each(model.exercise_names, function(idx, exercise) {
            matchingColumns[idx] = (filterText != '' && exercise.display_name_lower.indexOf(filterText) > -1);
            visibleColumns[idx] = matchingColumns[idx] || (filterText == '');
        });

        // Match rows with filter text
        $.each(model.exercise_list, function(idx, studentRow) {
            var foundMatchingExercise = false;
            var matchesFilter = filterText == '' || studentRow.nickname_lower.indexOf(filterText) > -1;

            $.each(studentRow.exercises, function(idx2, exercise) {
                if (exercise.status != '' && matchingColumns[idx2]) {
                    foundMatchingExercise = true;
                    return false;
                }
            });

            if (foundMatchingExercise || matchesFilter) {

                studentRow.visible = true;
                studentRow.highlight = matchesFilter && (filterText != '');

                if (matchesFilter) {
                    $.each(studentRow.exercises, function(idx2, exercise) {
                        if (exercise.status != '')
                            visibleColumns[idx2] = true;
                    });
                }
            } else {
                studentRow.visible = false;
                hiddenCount++;
            }
        });

        // "Struggling" filter
        if (filters['struggling'] || filters['recent']) {
            var filteredColumns = [];

            // Hide students who are not struggling in one of the visible columns
            $.each(model.exercise_list, function(idx, studentRow) {
                if (studentRow.visible) {
                    var foundValid = false;
                    studentRow.matchingCells = [];
                    $.each(studentRow.exercises, function(idx2, exercise) {
                        var valid = visibleColumns[idx2];
                        if (filters['struggling'] && exercise.status != 'Struggling') {
                            valid = false;
                        } else if (filters['recent'] && exercise.seconds_since_done > 60*60*24*filterRecentTime) {
                            valid = false;
                        }
                        if (valid) {
                            studentRow.matchingCells[idx2] = true;
                            filteredColumns[idx2] = true;
                            foundValid = true;
                        } else {
                            studentRow.matchingCells[idx2] = (exercise.status == '');
                        }
                    });
                    if (!foundValid) {
                        studentRow.visible = false;
                        hiddenCount++;
                    }
                }
            });

            // Hide columns that don't match the filter
            $.each(model.exercise_names, function(idx, exercise) {
                if (!matchingColumns[idx] && !filteredColumns[idx])
                    visibleColumns[idx] = false;
            });
        } else {
            $.each(model.exercise_list, function(idx, studentRow) {
                studentRow.matchingCells = null;
            });
        }

        this.hiddenStudentsModel.visible = (hiddenCount > 0);
        this.hiddenStudentsModel.hiddenCount = hiddenCount;

        temporaryDetachElement($('#module-progress'), function() {
            _.each(this.rowViews, function(rowView) {
                rowView.updateFilter(visibleColumns);
            });
            _.each(this.headingViews, function(colView) {
                colView.updateFilter(visibleColumns, matchingColumns);
            });
        }, this);

        var adjustData = this.preAdjustTable();
        temporaryDetachElement($('#module-progress'), function() {
            this.adjustTable(adjustData);
        }, this);
    },

    showBrowserRequirements: function() {
        $("#module-progress").replaceWith("<div class='graph-notification'>This chart requires a newer browser such as Google Chrome, Safari, Firefox, or Internet Explorer 8+.</div>");
    },

    hoverDiv: function() {
        if (!window.elProgressReportHoverDiv)
        {
            window.elProgressReportHoverDiv = $("<div class='exercise-info-hover' style='position:absolute;display:none;'></div>");
            $(document.body).append(window.elProgressReportHoverDiv);
        }
        return window.elProgressReportHoverDiv;
    },

    onHover: function() {
        var dtLastHover = window.dtLastHover = new Date();
        var self = this;
        setTimeout(function(){
            if (dtLastHover != window.dtLastHover) return;

            var sHover = $(self).find(".hover-content");
            if (sHover.length)
            {
                var jelHover = $(ProgressReport.hoverDiv());
                jelHover.html(sHover.html());

                var left = window.mouseX + 15;
                if (left + 150 > $(window).scrollLeft() + $(window).width()) left -= 150;

                var top = window.mouseY + 5;
                if (top + 115 > $(window).scrollTop() + $(window).height()) top -= 115;

                jelHover.css('left', left).css('top', top);
                jelHover.css('cursor', 'pointer');
                jelHover.show();
            }
        }, 100);
    },

    onUnhover: function() {
        window.dtLastHover = null;
        $(ProgressReport.hoverDiv()).hide();
    },

    onScroll: function() {

        var jelTable = $("#table_div");
        var jelHeader = $("#divHeader");
        var jelColumn = $("#firstcol");

        var leftTable = jelTable.scrollLeft();
        var topTable = jelTable.scrollTop();

        var leftHeader = jelHeader.scrollLeft(leftTable).scrollLeft();
        var topColumn = jelColumn.scrollTop(topTable).scrollTop();

        if (leftHeader < leftTable)
        {
            jelHeader.children().first().css("padding-right", 20);
            jelHeader.scrollLeft(leftTable);
        }

        if (topColumn < topTable)
        {
            jelColumn.children().first().css("padding-bottom", 20);
            jelColumn.scrollTop(topTable);
        }
    },

    onResize: function() {

        var width = $("#graph-content").width() - $("#firstTd").width() - 12;
        $(".sizeOnResize").width(width);

    },

    preAdjustTable: function() {

        var adjustData = { tableHeaderWidths: [] };

        // From http://fixed-header-using-jquery.blogspot.com/2009/05/scrollable-table-with-fixed-header-and.html
        //
        var columns = $('#divHeader th:visible');
        var colCount = columns.length-1; //get total number of column

        var m = 0;
        adjustData.brow = 'mozilla';

        jQuery.each(jQuery.browser, function(i, val) {
            if(val == true){
                adjustData.brow = i.toString();
            }
        });

        adjustData.tableDiv = $("#module-progress #table_div");
        adjustData.firstTd = $('#firstTd');
        adjustData.newFirstTdWidth = $('.tableFirstCol:visible').width();
        adjustData.tableHeaderHeight = adjustData.firstTd.height();

        $('#table_div td:visible:lt(' + colCount +')').each(function(index, element) {
            var colIdx = $(this).attr('data-id');
            var cellWidth = $(this).width();
            if (adjustData.brow == 'msie'){
                cellWidth -= 2; //In IE there is difference of 2 px
            }
            adjustData.tableHeaderWidths[colIdx] = { 'width': cellWidth };
        });

        columns.each(function(index, element){
            var colIdx = $(element).attr('data-id');
            if (colIdx) {
                if (adjustData.tableHeaderWidths[colIdx]) {
                    adjustData.tableHeaderWidths[colIdx].header = $(this).find('div.tableHeader');
                    adjustData.tableHeaderWidths[colIdx].headerTh = $(this);
                }
            }
        });

        return adjustData;
    },

    adjustTable: function(adjustData) {

        if (adjustData.brow == 'chrome' || adjustData.brow == 'safari') {
            adjustData.tableDiv.css('top', '1px');
        }

        adjustData.firstTd.css("width",adjustData.newFirstTdWidth);//for adjusting first td
        $.each(adjustData.tableHeaderWidths, function(idx, headerWidth) {
            if (headerWidth)
                if (headerWidth.width >= 0) {
                    $(headerWidth.header).width(headerWidth.width);
                    $(headerWidth.headerTh).height(adjustData.tableHeaderHeight);
                } else {
                    $(headerWidth.header).attr('style','');
                }
        });
    }
};
