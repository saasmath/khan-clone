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
    profile: null,
    profileRoot: "",

    /**
     * Called to initialize the profile page. Passed in with JSON information
     * rendered from the server. See templates/viewprofile.html for details.
     */
    init: function(json) {
        this.profile = new UserCardModel(json.profileData);
        this.profileRoot = json.profileRoot;
        UserCardView.countVideos = json.countVideos;
        UserCardView.countExercises = json.countExercises;

        Profile.render();
        Profile.router = new Profile.TabRouter();
        Backbone.history.start({
            pushState: true,
            root: this.profileRoot
        });

        // Remove goals from IE<=8
        $(".lte8 .goals-accordion-content").remove();

        // Init Highcharts global options
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

        // Delegate clicks for badge navigation
        $("#individual_report #achievements #achievement-list > ul").delegate("li", "click", function(e) {
            var category = $(this).attr("id");
            var clickedBadge = $(this);

            $("#badge-container").css("display", "");
            clickedBadge.siblings().removeClass("selected");

            if ($("#badge-container > #" + category).is(":visible")) {
               if (clickedBadge.parents().hasClass("standard-view")) {
                   $("#badge-container > #" + category).slideUp(300, function() {
                           $("#badge-container").css("display", "none");
                           clickedBadge.removeClass("selected");
                       });
               }
               else {
                   $("#badge-container > #" + category).hide();
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

        // Delegate clicks for tab navigation
        $(".profile-navigation .vertical-tab-list").delegate("a", "click", function(event) {
            // TODO: Make sure middle-click + windows control-click Do The Right Thing
            // in a reusable way
            if (!event.metaKey) {
                event.preventDefault();
                var route = $(this).attr("href").replace(
                        Profile.profileRoot, "");
                Profile.router.navigate(route, true);
            }
        });

        // Delegate clicks for recent badge-related activity
        $(".achievement .ach-text").delegate("a", "click", function(event) {
            // TODO: ditto above
            if (!event.metaKey) {
                event.preventDefault();
                Profile.router.navigate("/achievements", true);
                $("#achievement-list ul li#category-" + $(this).data("category")).click();
            }
        });

        // Bind event handlers for sharing controls on recent activity
        $(".share-link").hide();
        $(".sharepop").hide();

        $(".achievement,.exercise,.video").hover(
            function() {
                $(this).find(".share-link").show();
                },
            function() {
                $(this).find(".share-link").hide();
                $(this).find(".sharepop").hide();
              });

        $(".share-link").click(function() {
            if ($.browser.msie && (parseInt($.browser.version, 10) < 8)) {
                $(this).next(".sharepop").toggle();
            } else {
                $(this).next(".sharepop").toggle(
                        "drop", { direction: "up" }, "fast");
            }
            return false;
        });
    },

    TabRouter: Backbone.Router.extend({
        routes: {
            "": "showDefault",
            "/achievements": "showAchievements",
            "/goals": "showGoals",
            "/vital-statistics": "showVitalStatistics",
            "/vital-statistics/exercise-problems/:exercise": "showExerciseProblems",
            "/vital-statistics/:graph/:timePeriod": "showVitalStatisticsForTimePeriod",
            "/vital-statistics/:graph": "showVitalStatistics"
        },

        showDefault: function() {
            $("#tab-content-user-profile").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-user-profile").attr("rel"));
        },

        // TODO: must send TZ offset
        showVitalStatistics: function(graph, exercise, timeURLParameter) {
            var graph = graph || "activity",
                exercise = exercise || "addition_1",
                timeURLParameter = timeURLParameter || "",
                emailEncoded = encodeURIComponent(USER_EMAIL),
                translation = {
                    "activity": "/profile/graph/activity?student_email=" + emailEncoded,
                    "focus": "/profile/graph/focus?student_email=" + emailEncoded,
                    "exercise-progress-over-time": "/profile/graph/exercisesovertime?student_email=" + emailEncoded,
                    "exercise-progress": "/api/v1/user/exercises?email=" + emailEncoded,
                    "exercise-problems": "/profile/graph/exerciseproblems?" +
                                            "exercise_name=" + exercise +
                                            "&" + "student_email=" + emailEncoded
                },
                href = translation[graph] + timeURLParameter,
                jelGraphLinkHeader = $(".graph-link-header[href$='" + graph + "']");

            $("#tab-content-vital-statistics").show()
                .siblings().hide();

            if (jelGraphLinkHeader.length) {
                var index = jelGraphLinkHeader.index(),
                    isSubLink = jelGraphLinkHeader.hasClass("graph-sub-link");

                if (!isSubLink) {
                    $(".graph-link").css("background-color", "")
                        .eq(index).css("background-color", "#eee");
                }
            }

            this.activateRelatedTab($("#tab-content-vital-statistics").attr("rel") + " " + graph);
            var prettyGraphName = graph.replace(/-/gi," ");
            var sheetTitle = $(".profile-graph-title");
            var nickname = Profile.profile.get("nickname");
            if ( graph == "exercise-problems" ) {
                var prettyExName = exercise.replace(/_/gi," ");
                sheetTitle.html( nickname + " &raquo; " + prettyGraphName + " &raquo; " + prettyExName);
            }
            else {
                sheetTitle.html( nickname + " &raquo; " + prettyGraphName);
            }
            Profile.loadGraph(href);
        },

        showExerciseProblems: function(exercise) {
            this.showVitalStatistics("exercise-problems", exercise);
        },

        showVitalStatisticsForTimePeriod: function(graph, timePeriod) {
            var translation = {
                    "today": "&dt_start=today",
                    "yesterday": "&dt_start=yesterday",
                    "last-week": "&dt_start=lastweek&dt_end=today",
                    "last-month": "&dt_start=lastmonth&dt_end=today"
                },
                timeURLParameter = translation[timePeriod];

            this.showVitalStatistics(graph, null, timeURLParameter);
        },

        showAchievements: function() {
            $("#tab-content-achievements").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-achievements").attr("rel"));
        },

        showGoals: function() {
            $("#tab-content-goals").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-goals").attr("rel"));
        },

        activateRelatedTab: function(rel) {
            $(".profile-navigation .vertical-tab-list a").removeClass("active-tab");
            $("a[rel$='" + rel + "']").addClass("active-tab");
        }
    }),

    loadGraph: function(href, fNoHistoryEntry) {
        var apiCallbacksTable = {
            "/api/v1/user/exercises": this.renderExercisesTable
        };
        if (!href) return;

        if (this.fLoadingGraph) {
            setTimeout(function() {Profile.loadGraph(href);}, 200);
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
            dataType: apiCallback ? "json" : "html",
            success: function(data) {
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

        this.showGraphThrobber(false);

        var start = (new Date).getTime();
        if (apiCallback) {
            apiCallback(data, href);
        } else {
            $("#graph-content").html(data);
        }
        var diff = (new Date).getTime() - start;
        KAConsole.log("API call rendered in " + diff + " ms.");
    },

    renderUserGoals: function(data, href) {
        current_goals = [];
        completed_goals = [];
        abandoned_goals = [];

        var qs = Profile.parseQueryString(href);
        // We don't handle the difference between API calls requiring email and
        // legacy calls requiring student_email very well, so this page gets
        // called with both. Need to fix the root cause (and hopefully redo all
        // the URLs for this page), but for now just be liberal in what we
        // accept.
        var qsEmail = qs.email || qs.student_email || null;
        var viewingOwnGoals = qsEmail === null || qsEmail === USER_EMAIL;

        $.each(data, function(idx, goal) {
            if (goal.completed) {
                if (goal.abandoned)
                    abandoned_goals.push(goal);
                else
                    completed_goals.push(goal);
            } else {
                current_goals.push(goal);
            }
        });
        if (viewingOwnGoals)
            GoalBook.reset(current_goals);
        else
            CurrentGoalBook = new GoalCollection(current_goals);
        CompletedGoalBook = new GoalCollection(completed_goals);
        AbandonedGoalBook = new GoalCollection(abandoned_goals);

        $("#graph-content").html('<div id="current-goals-list"></div><div id="completed-goals-list"></div><div id="abandoned-goals-list"></div>');

        Profile.goalsViews = {};
        Profile.goalsViews.current = new GoalProfileView({
            el: "#current-goals-list",
            model: viewingOwnGoals ? GoalBook : CurrentGoalBook,
            type: "current",
            readonly: !viewingOwnGoals
        });
        Profile.goalsViews.completed = new GoalProfileView({
            el: "#completed-goals-list",
            model: CompletedGoalBook,
            type: "completed",
            readonly: true
        });
        Profile.goalsViews.abandoned = new GoalProfileView({
            el: "#abandoned-goals-list",
            model: AbandonedGoalBook,
            type: "abandoned",
            readonly: true
        });

        Profile.userGoalsHref = href;
        Profile.showGoalType("current");

        if (completed_goals.length > 0) {
            $("#goal-show-completed-link").parent().show();
        } else {
            $("#goal-show-completed-link").parent().hide();
        }
        if (abandoned_goals.length > 0) {
            $("#goal-show-abandoned-link").parent().show();
        } else {
            $("#goal-show-abandoned-link").parent().hide();
        }

        if (viewingOwnGoals) {
            $(".new-goal").addClass("green").removeClass("disabled").click(function(e) {
                e.preventDefault();
                window.newGoalDialog.show();
            });
        }
    },

    showGoalType: function(type) {
        if (Profile.goalsViews) {
            $.each(["current", "completed", "abandoned"], function(idx, atype) {
                if (type == atype) {
                    Profile.goalsViews[atype].show();
                    $("#goal-show-" + atype + "-link").addClass("graph-sub-link-selected");
                } else {
                    Profile.goalsViews[atype].hide();
                    $("#goal-show-" + atype + "-link").removeClass("graph-sub-link-selected");
                }
            });
        }
    },

    renderStudentGoals: function(data, href) {
        var studentGoalsViewModel = {
            rowData: [],
            sortDesc: "",
            filterDesc: ""
        };

        $.each(data, function(idx1, student) {
            student.goal_count = 0;
            student.most_recent_update = null;
            student.profile_url = "/profile?student_email=" + student.email + "#/api/v1/user/goals?email=" + student.email;

            if (student.goals != undefined && student.goals.length > 0) {
                $.each(student.goals, function(idx2, goal) {
                    // Sort objectives by status
                    var progress_count = 0;
                    var found_struggling = false;

                    goal.objectiveWidth = 100 / goal.objectives.length;
                    goal.objectives.sort(function(a, b) { return b.progress - a.progress; });

                    $.each(goal.objectives, function(idx3, objective) {
                        Goal.calcObjectiveDependents(objective, goal.objectiveWidth);

                        if (objective.status == "proficient")
                            progress_count += 1000;
                        else if (objective.status == "started" || objective.status == "struggling")
                            progress_count += 1;

                        if (objective.status == "struggling") {
                            found_struggling = true;
                            objective.struggling = true;
                        }
                        objective.statusCSS = objective.status ? objective.status : "not-started";

                        objective.objectiveID = idx3;
                    });

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

        var template = Templates.get("profile.profile-class-goals");
        $("#graph-content").html(template(studentGoalsViewModel));

        $("#class-student-goal .goal-row").each(function() {
            var jRowEl = $(this);
            var goalViewModel = studentGoalsViewModel.rowData[jRowEl.attr("data-id")];
            goalViewModel.rowElement = this;
            goalViewModel.countElement = jRowEl.find(".goal-count");
            goalViewModel.startTimeElement = jRowEl.find(".goal-start-time");
            goalViewModel.updateTimeElement = jRowEl.find(".goal-update-time");

            Profile.AddObjectiveHover(jRowEl);

            jRowEl.find("a.objective").each(function() {
                var obj = goalViewModel.goal.objectives[$(this).attr("data-id")];
                obj.blockElement = this;

                if (obj.internal_id !== "" &&
                    (obj.type === "GoalObjectiveExerciseProficiency" ||
                     obj.type === "GoalObjectiveAnyExerciseProficiency")
                ) {
                    $(this).click(function(e) {
                        e.preventDefault();
                        Profile.collapseAccordion();
                        var url = Profile.exerciseProgressUrl(obj.internal_id,
                            goalViewModel.student.email);
                        Profile.loadGraph(url);
                    });
                }
            });
        });

        $("#student-goals-sort").change(function() { Profile.sortStudentGoals(studentGoalsViewModel); });

        $("input.student-goals-filter-check").change(function() { Profile.filterStudentGoals(studentGoalsViewModel); });
        $("#student-goals-search").keyup(function() { Profile.filterStudentGoals(studentGoalsViewModel); });

        Profile.sortStudentGoals(studentGoalsViewModel);
        Profile.filterStudentGoals(studentGoalsViewModel);
    },
    sortStudentGoals: function(studentGoalsViewModel) {
        var sort = $("#student-goals-sort").val();
        var show_updated = false;

        if (sort == "name") {
            studentGoalsViewModel.rowData.sort(function(a, b) {
                if (b.student.nickname > a.student.nickname)
                    return -1;
                if (b.student.nickname < a.student.nickname)
                    return 1;
                return a.goal_idx - b.goal_idx;
            });

            studentGoalsViewModel.sortDesc = "student name";
            show_updated = false; // started

        } else if (sort == "progress") {
            studentGoalsViewModel.rowData.sort(function(a, b) {
                return b.progress_count - a.progress_count;
            });

            studentGoalsViewModel.sortDesc = "goal progress";
            show_updated = true; // updated

        } else if (sort == "created") {
            studentGoalsViewModel.rowData.sort(function(a, b) {
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

            studentGoalsViewModel.sortDesc = "goal creation time";
            show_updated = false; // started

        } else if (sort == "updated") {
            studentGoalsViewModel.rowData.sort(function(a, b) {
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

            studentGoalsViewModel.sortDesc = "last work logged time";
            show_updated = true; // updated
        }

        var container = $("#class-student-goal").detach();
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
        container.insertAfter("#class-goal-filter-desc");

        Profile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },
    updateStudentGoalsFilterText: function(studentGoalsViewModel) {
        var text = "Sorted by " + studentGoalsViewModel.sortDesc + ". " + studentGoalsViewModel.filterDesc + ".";
        $("#class-goal-filter-desc").html(text);
    },
    filterStudentGoals: function(studentGoalsViewModel) {
        var filter_text = $.trim($("#student-goals-search").val().toLowerCase());
        var filters = {};
        $("input.student-goals-filter-check").each(function(idx, element) {
            filters[$(element).attr("name")] = $(element).is(":checked");
        });

        studentGoalsViewModel.filterDesc = "";
        if (filters["most-recent"]) {
            studentGoalsViewModel.filterDesc += "most recently worked on goals";
        }
        if (filters["in-progress"]) {
            if (studentGoalsViewModel.filterDesc != "") studentGoalsViewModel.filterDesc += ", ";
            studentGoalsViewModel.filterDesc += "goals in progress";
        }
        if (filters["struggling"]) {
            if (studentGoalsViewModel.filterDesc != "") studentGoalsViewModel.filterDesc += ", ";
            studentGoalsViewModel.filterDesc += "students who are struggling";
        }
        if (filter_text != "") {
            if (studentGoalsViewModel.filterDesc != "") studentGoalsViewModel.filterDesc += ", ";
            studentGoalsViewModel.filterDesc += 'students/goals matching "' + filter_text + '"';
        }
        if (studentGoalsViewModel.filterDesc != "")
            studentGoalsViewModel.filterDesc = "Showing only " + studentGoalsViewModel.filterDesc;
        else
            studentGoalsViewModel.filterDesc = "No filters applied";

        var container = $("#class-student-goal").detach();

        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            var row_visible = true;

            if (filters["most-recent"]) {
                row_visible = row_visible && (!row.goal || (row.goal == row.student.most_recent_update));
            }
            if (filters["in-progress"]) {
                row_visible = row_visible && (row.goal && (row.progress_count > 0));
            }
            if (filters["struggling"]) {
                row_visible = row_visible && (row.struggling);
            }
            if (row_visible) {
                if (filter_text == "" || row.student.nickname.toLowerCase().indexOf(filter_text) >= 0) {
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            $(objective.blockElement).removeClass("matches-filter");
                        });
                    }
                } else {
                    row_visible = false;
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            if ((objective.description.toLowerCase().indexOf(filter_text) >= 0)) {
                                row_visible = true;
                                $(objective.blockElement).addClass("matches-filter");
                            } else {
                                $(objective.blockElement).removeClass("matches-filter");
                            }
                        });
                    }
                }
            }

            if (row_visible)
                $(row.rowElement).show();
            else
                $(row.rowElement).hide();

            if (filters["most-recent"])
                row.countElement.hide();
            else
                row.countElement.show();
        });

        container.insertAfter("#class-goal-filter-desc");

        Profile.updateStudentGoalsFilterText(studentGoalsViewModel);
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
        var templateContext = [];

        for (var i = 0, exercise; exercise = data[i]; i++) {
            var stat = "Not started";
            var color = "";
            var states = exercise["exercise_states"];
            var totalDone = exercise["total_done"];

            if (states["reviewing"]) {
                stat = "Review";
                color = "review light";
            } else if (states["proficient"]) {
                // TODO: handle implicit proficiency - is that data in the API?
                // (due to proficiency in a more advanced module)
                stat = "Proficient";
                color = "proficient";
            } else if (states["struggling"]) {
                stat = "Struggling";
                color = "struggling";
            } else if (totalDone > 0) {
                stat = "Started";
                color = "started";
            }

            if (color) {
                color = color + " action-gradient seethrough";
            } else {
                color = "transparent";
            }
            var model = exercise["exercise_model"];
            templateContext.push({
                "name": model["name"],
                "color": color,
                "status": stat,
                "shortName": model["short_display_name"] || model["display_name"],
                "displayName": model["display_name"],
                "progress": Math.floor(exercise["progress"] * 100) + "%",
                "totalDone": totalDone
            });
        }
        var template = Templates.get("profile.exercise_progress");
        $("#graph-content").html(template({ "exercises": templateContext }));

        Profile.hoverContent($("#module-progress .student-module-status"));
        $("#module-progress .student-module-status").click(function(e) {
            $("#info-hover-container").hide();
            // Extract the name from the ID, which has been prefixed.
            var exerciseName = this.id.substring("exercise-".length);
            Profile.router.navigate("/vital-statistics/exercise-problems/" + exerciseName, true);
        });
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
        var parts = url.split("?");
        if (parts.length == 2) {
            var querystring = parts[1].split("&");
            for (var i = 0; i < querystring.length; i++) {
                var kv = querystring[i].split("=");
                if (kv[0].length > 0) { //fix trailing &
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
        kvjoin = kvjoin || "=";
        eljoin = eljoin || "&";
        qs = [];
        for (var key in hash) {
            if (hash.hasOwnProperty(key))
                qs.push(key + kvjoin + hash[key]);
        }
        return qs.join(eljoin);
    },

    hoverContent: function(elements) {
        var lastHoverTime;
        var mouseX;
        var mouseY;

        elements.hover(
            function(e) {
                var hoverTime = +(new Date());
                lastHoverTime = hoverTime;
                mouseX = e.pageX;
                mouseY = e.pageY;
                var el = this;
                setTimeout(function() {
                    if (hoverTime != lastHoverTime) {
                        return;
                    }

                    var hoverData = $(el).children(".hover-data");
                    var html = $.trim(hoverData.html());
                    if (html) {
                        var jelGraph = $("#graph-content");
                        var leftMax = jelGraph.offset().left +
                                jelGraph.width() - 150;
                        var left = Math.min(mouseX + 15, leftMax);

                        var jHoverEl = $("#info-hover-container");
                        if (jHoverEl.length === 0) {
                            jHoverEl = $('<div id="info-hover-container"></div>').appendTo("body");
                        }
                        jHoverEl
                            .html(html)
                            .css({left: left, top: mouseY + 5})
                            .show();
                    }
                }, 100);
            },
            function(e) {
                lastHoverTime = null;
                $("#info-hover-container").hide();
            }
        );
    },

    AddObjectiveHover: function(element) {
        Profile.hoverContent(element.find(".objective"));
    },
    render: function() {
        var profileTemplate = Templates.get("profile.profile");

        Handlebars.registerPartial("vital-statistics", Templates.get("profile.vital-statistics"));

        $("#profile-content").html(
                profileTemplate({profileRoot: this.profileRoot}));

        // Show only the user card tab,
        // since the Backbone default route isn't triggered
        // when visiting khanacademy.org/profile
        $("#tab-content-user-profile").show()
            .siblings().hide();

        Profile.populateUserCard();
        Profile.populateAchievements();
        Profile.populateGoals();

        // TODO: Might there be a better way
        // for server-side + client-side to co-exist in harmony?
        $("#tab-content-user-profile").append($("#server-side-recent-activity").html());
    },

    populateUserCard: function() {
        var view = new UserCardView({model: this.profile});

        $(".user-info-container").html(view.render().el);
    },

    populateAchievements: function() {
        // Render the public badge list, as that's ready immediately.
        var publicBadgeList = new Badges.BadgeList(
                this.profile.get("publicBadges"));
        publicBadgeList.setSaveUrl("/api/v1/user/badges/public");
        var displayCase = new Badges.DisplayCase({ model: publicBadgeList });
        $(".sticker-book").append(displayCase.render().el);

        // Asynchronously load the full badge information in the background.
        $.ajax({
            type: "GET",
            url: "/api/v1/user/badges",
            data: {
                casing: "camel",
                email: USER_EMAIL
              },
            dataType: "json",
            success: function(data) {

                // TODO: save and cache these objects
                var fullBadgeList = new Badges.UserBadgeList();

                var collection = data["badgeCollections"];
                $.each(collection, function(i, categoryJson) {
                    $.each(categoryJson["userBadges"], function(j, json) {
                        fullBadgeList.add(new Badges.UserBadge(json));
                    });
                });
                displayCase.setFullBadgeList(fullBadgeList);

                // TODO: make the rendering of the full badge page use the models above
                // and consolidate the information

                var badgeInfo = [
                        {
                            icon: "/images/badges/meteorite-medium.png",
                            className: "bronze",
                            label: "Meteorite"
                        },
                        {
                            icon: "/images/badges/moon-medium.png",
                            className: "silver",
                            label: "Moon"
                        },
                        {
                            icon: "/images/badges/earth-medium.png",
                            className: "gold",
                            label: "Earth"
                        },
                        {
                            icon: "/images/badges/sun-medium.png",
                            className: "diamond",
                            label: "Sun"
                        },
                        {
                            icon: "/images/badges/eclipse-medium.png",
                            className: "platinum",
                            label: "Black Hole"
                        },
                        {
                            icon: "/images/badges/master-challenge-blue.png",
                            className: "master",
                            label: "Challenge"
                        }
                    ];

                // Because we show the badges in reverse order,
                // from challenge/master/category-5 to meteorite/bronze/category-0
                Handlebars.registerHelper("reverseEach", function(context, block) {
                    var result = "";
                    for (var i = context.length - 1; i >= 0; i--) {
                        result += block(context[i]);
                    }
                    return result;
                });

                Handlebars.registerHelper("toMediumIconSrc", function(category) {
                    return badgeInfo[category].icon;
                });

                Handlebars.registerHelper("toBadgeClassName", function(category) {
                    return badgeInfo[category].className;
                });

                Handlebars.registerHelper("toBadgeLabel", function(category, fStandardView) {
                    var label = badgeInfo[category].label;

                    if (fStandardView) {
                        if (label === "Challenge") {
                            label += " Patches";
                        } else {
                            label += " Badges";
                        }
                    }
                    return label;
                });

                Handlebars.registerPartial(
                        "badge-container",
                        Templates.get("profile.badge-container"));
                Handlebars.registerPartial(
                        "badge",
                        Templates.get("profile.badge"));
                Handlebars.registerPartial(
                        "user-badge",
                        Templates.get("profile.user-badge"));

                $.each(data["badgeCollections"], function(collectionIndex, collection) {
                    $.each(collection["userBadges"], function(badgeIndex, badge) {
                        var targetContextNames = badge["targetContextNames"];
                        var numHidden = targetContextNames.length - 1;
                        badge["visibleContextName"] = targetContextNames[0] || "";
                        badge["listContextNamesHidden"] = $.map(
                            targetContextNames.slice(1),
                            function(name, nameIndex) {
                                return {
                                    name: name,
                                    isLast: (nameIndex === numHidden - 1)
                                };
                            });
                        badge["hasMultiple"] = (badge["count"] > 1);
                    });
                });

                // TODO: what about mobile-view?
                data.fStandardView = true;

                var achievementsTemplate = Templates.get("profile.achievements");
                $("#tab-content-achievements").html(achievementsTemplate(data));

                $("#achievements #achievement-list > ul li").click(function() {
                     var category = $(this).attr("id");
                     var clickedBadge = $(this);

                     $("#badge-container").css("display", "");

                     clickedBadge.siblings().removeClass("selected");

                     if ($("#badge-container > #" + category).is(":visible")) {
                        if (clickedBadge.parents().hasClass("standard-view")) {
                            $("#badge-container > #" + category).slideUp(300, function() {
                                    $("#badge-container").css("display", "none");
                                    clickedBadge.removeClass("selected");
                                });
                        }
                        else {
                            $("#badge-container > #" + category).hide();
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
                $("abbr.timeago").timeago();
            }
        });
    },

    populateGoals: function() {
        $.ajax({
            type: "GET",
            url: "/api/v1/user/goals",
            data: {email: USER_EMAIL},
            dataType: "json",
            success: function(data) {
                GoalProfileViewsCollection.render(data, "/api/v1/user/goals?email=" + USER_EMAIL);
            }
        });
    }
};

