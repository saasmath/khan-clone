/**
 * Code to handle the logic for the class profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

var ClassProfile = {
    version: 0,
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

        $("#nav-accordion").on("click", ".graph-link", function(evt) {
            if (!evt.metaKey) {
                evt.preventDefault();

                var route = $(evt.currentTarget).attr("href");
                route = route.substring("/class_profile".length);

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

        ClassProfile.router = new ClassProfile.TabRouter();
        Backbone.history.start({
            pushState: true,
            root: "/class_profile"
        });
    },

    TabRouter: Backbone.Router.extend({
        routes: {
            "": "showGraph",
            "/:graph": "showGraph"
        },

        hrefLookup_: {
            "progress-report": "/api/v1/user/students/progressreport",
            "progress-summary": "/api/v1/user/students/progress/summary",
            "daily-activity": "/profile/graph/classtime",
            "exercise-progress-over-time": "/profile/graph/classexercisesovertime",
            "points-per-minute": "/profile/graph/classenergypointsperminute",
            "goals": "/api/v1/user/students/goals"
        },

        showGraph: function(graph) {
            var graph = graph || "progress-report",
                href = this.hrefLookup_[graph],
                accordionSelector = ".graph-link-header[href$='" + graph + "']";

            if (!href) {
                return;
            }

            $("#stats-nav #nav-accordion").accordion("activate", accordionSelector);
            ClassProfile.loadGraph(href, true);
            ClassProfile.loadFilters(href);
        }
    }),

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

    loadFilters: function(href){
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

    finishLoadGraph: function(data, href, fNoHistoryEntry, apiCallback) {

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
