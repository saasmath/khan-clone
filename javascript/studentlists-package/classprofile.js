/**
 * Code to handle the logic for the class profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

// TODO(marcia): Fix coach_email URL param action (for debugging only? Are there other use cases?)
// TODO(marcia): Check whether this breaks any "coworker" behavior

var ClassProfile = {
    version: 0,
    fLoadingGraph: false,
    fLoadedGraph: false,
    root: "/class_profile",

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

        $("#nav-accordion").on("click", ".graph-link", function(evt) {
            if (!evt.metaKey) {
                evt.preventDefault();

                var route = $(evt.currentTarget).attr("href");
                route = route.substring(ClassProfile.root.length);

                ClassProfile.router.navigate(route, true);
            }
        });

        // remove goals from IE<=8
        $(".lte8 .goals-accordion-content").remove();

        $("#stats-nav #nav-accordion")
            .accordion({
                header:".header",
                active:".graph-link-selected",
                autoHeight: false,
                clearStyle: true
            });

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
                e.preventDefault();

                if (menu.css('display') == 'none') {
                    menu.show().menu("activate", e, $('#studentlists_dropdown li[data-selected=selected]')).focus();
                } else {
                    menu.hide();
                }
            });

            // get initially selected list
            var list_id = $dropdown.children('li[data-selected=selected]').data('list_id');
            var student_list = ClassProfile.getStudentListFromId(list_id);
            $dropdown.data('selected', student_list);
        }

        $("#targetDatepicker").datepicker().change(function(){
            ClassProfile.router.trigger("change:date", this.value);
        });

        ClassProfile.router = new ClassProfile.TabRouter({startingStudentList: list_id});

        Backbone.history.start({
            pushState: true,
            root: this.root
        });
    },

    TabRouter: Backbone.Router.extend({
        routes: {
            "": "showDefault",
            "/:graph": "showGraph",
            "/:graph/:studentList": "showGraph"
        },

        hrefLookup_: {
            "progress-report": "/api/v1/user/students/progressreport",
            "progress-summary": "/api/v1/user/students/progress/summary",
            "daily-activity": "/profile/graph/classtime",
            "exercise-progress-over-time": "/profile/graph/classexercisesovertime",
            "points-per-minute": "/profile/graph/classenergypointsperminute",
            "goals": "/api/v1/user/students/goals"
        },

        currGraph_: "progress-report",
        currStudentList_: "allstudents",
        currDate_: "",

        initialize: function(options) {
            if (options && options.startingStudentList) {
                this.currStudentList_ = options.startingStudentList;
            }

            this.bind("change:studentList", this.onStudentListChange_, this);
            this.bind("change:date", this.onDateChange_, this);
        },

        showDefault: function() {
            this.navigate("/progress-report", false);
        },

        showGraph: function(graph, studentList) {
            var href = this.hrefLookup_[graph],
                accordionSelector = ".graph-link-header[href$='" + graph + "']";

            if (!href) {
                return;
            }

            this.currGraph_ = graph;
            if (studentList) {
                this.currStudentList_ = studentList;
            }

            // Always have student list id in the url
            this.navigate("/" + this.currGraph_ + "/" + this.currStudentList_, false);

            // Expand accordion section
            $("#stats-nav #nav-accordion").accordion("activate", accordionSelector);
            // Load sort and search UI
            ClassProfile.loadFilters(href);

            // Build url from which to load graph
            var params = {
                "list_id": this.currStudentList_
            };
            if ((graph === "daily-activity") && this.currDate_) {
                params["dt"] = this.currDate_;
            }
            href += "?" + $.param(params);

            ClassProfile.loadGraph(href);
        },

        onStudentListChange_: function(studentList) {
            this.navigate("/" + this.currGraph_ + "/" + studentList, true);
        },

        onDateChange_: function(date) {
            this.currDate_ = date;
            this.showGraph(this.currGraph_, this.currStudentList_);
        }
    }),

    loadFilters: function(href){
        // fix the hrefs for each filter
        var a = $("#stats-filters a[href^=\"" + href + "\"]").parent();
        $("#stats-filters .filter:visible").not(a).slideUp("slow");
        a.slideDown();
    },

    loadGraph: function(href) {
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
                ClassProfile.finishLoadGraph(data, href, apiCallback);
            },
            error: function() {
                ClassProfile.finishLoadGraphError();
            }
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },

    finishLoadGraph: function(data, href, apiCallback) {

        this.fLoadingGraph = false;

        this.showGraphThrobber(false);

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

    showGraphThrobber: function(fVisible) {
        if (fVisible) {
            $("#graph-progress-bar").progressbar({value: 100}).slideDown("fast");
        } else {
            $("#graph-progress-bar").slideUp("fast", function() {
                $(this).hide();
            });
        }
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

        // Triggering the router event updates the url and loads the correct graph
        ClassProfile.router.trigger("change:studentList", ui.item.data('list_id'));

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
                                    + "/vital-statistics/exercise-problems/"
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

        var template = Templates.get("studentlists.class-progress-report");

        $("#graph-content").html(template(data));
        ProgressReport.init(data);
    }
};
