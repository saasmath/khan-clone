/**
 * Code to handle the logic for the profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

var Profile = {
    version: 0,
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
        this.profile = new ProfileModel(json.profileData);
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

        var currentGoals = window.GoalBook.map( function(g){ return g.get("title"); });
        _( $(".add-goal") ).map( function( elt ){
            var button = $( elt );
            var badge = button.closest( ".achievement-badge" );
            var goalTitle = badge.find( ".achievement-title" ).text();

            // remove +goal button if present in list of active goals
            if( _.indexOf( currentGoals, goalTitle ) > -1){

                button.remove();

            // add +goal behavior to button, once.
            } else {

                button.one("click", function(){
                    var goalObjectives = _( badge.data("objectives") ).map( function( exercise ){
                        return {
                            "type" : "GoalObjectiveExerciseProficiency",
                            "internal_id" : exercise
                        };
                    });

                    var goal = new Goal({
                        title: goalTitle,
                        objectives: goalObjectives
                    });

                    window.GoalBook.add(goal);

                    goal.save()
                        .fail(function(err) {
                            var error = err.responseText;
                            button.addClass("failure")
                                .text("oh no!").attr("title","This goal could not be saved.");
                            KAConsole.log("Error while saving new badge goal", goal);
                            window.GoalBook.remove(goal);
                        })
                        .success(function(){
                            button.text("Goal Added!").addClass("success");
                            badge.find(".energy-points-badge").addClass("goal-added");
                        });
                });
            }
        });

        // Delegate clicks for tab navigation
        $(".profile-navigation .vertical-tab-list").delegate("a",
                "click", this.onNavigationElementClicked_);

        // Delegate clicks for vital statistics time period navigation
        $("#tab-content-vital-statistics").delegate(".graph-date-picker a",
                "click", this.onNavigationElementClicked_);

        $("#tab-content-goals").delegate(".graph-picker .type a",
                "click", this.onNavigationElementClicked_);

        // Delegate clicks for recent badge-related activity
        $(".achievement .ach-text").delegate("a", "click", function(event) {
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
            "/goals/:type": "showGoals",
            "/goals": "showGoals",
            "/vital-statistics": "showVitalStatistics",
            "/vital-statistics/exercise-problems/:exercise": "showExerciseProblems",
            "/vital-statistics/:graph/:timePeriod": "showVitalStatisticsForTimePeriod",
            "/vital-statistics/:graph": "showVitalStatistics"
        },

        showDefault: function() {
            $("#tab-content-user-profile").show().siblings().hide();
            this.activateRelatedTab($("#tab-content-user-profile").attr("rel"));
        },

        // TODO: must send TZ offset
        showVitalStatistics: function(graph, exercise, timePeriod) {
            var graph = graph || "activity",
                exercise = exercise || "addition_1",
                timePeriod = timePeriod || "last-week",
                emailEncoded = encodeURIComponent(USER_EMAIL),
                hrefLookup = {
                    "activity": "/profile/graph/activity?student_email=" + emailEncoded,
                    "focus": "/profile/graph/focus?student_email=" + emailEncoded,
                    "exercise-progress-over-time": "/profile/graph/exercisesovertime?student_email=" + emailEncoded,
                    "exercise-progress": "/api/v1/user/exercises?email=" + emailEncoded,
                    "exercise-problems": "/profile/graph/exerciseproblems?" +
                                            "exercise_name=" + exercise +
                                            "&" + "student_email=" + emailEncoded
                },
                timePeriodLookup = {
                    "today": "&dt_start=today",
                    "yesterday": "&dt_start=yesterday",
                    "last-week": "&dt_start=lastweek&dt_end=today",
                    "last-month": "&dt_start=lastmonth&dt_end=today"
                },
                timeURLParameter = timePeriod ? timePeriodLookup[timePeriod] : "",
                href = hrefLookup[graph] + timeURLParameter;

            // Known bug: the wrong graph-date-picker item is selected when
            // server man decides to show 30 days instead of the default 7.
            // See redirect_for_more_data in util_profile.py for more on this tragedy.
            $("#tab-content-vital-statistics").show()
                .find(".vital-statistics-description ." + graph).show()
                    .find(".graph-date-picker .tabrow .last-week").addClass("selected")
                        .siblings().removeClass("selected").end()
                    .end()
                    .siblings().hide().end()
                .end().siblings().hide();

            this.activateRelatedTab($("#tab-content-vital-statistics").attr("rel") + " " + graph);
            var prettyGraphName = graph.replace(/-/gi, " ");
            if (graph == "exercise-problems") {
                var prettyExName = exercise.replace(/_/gi, " ");
                this.updateTitleBreadcrumbs([prettyGraphName, prettyExName]);
            }
            else {
                this.updateTitleBreadcrumbs([prettyGraphName]);
            }

            if (Profile.profile.get("email")) {
                // If we have access to the profiled person's email, load real data.
                Profile.loadGraph(href);
            } else {
                // Otherwise, show some fake stuff.
                Profile.renderFakeGraph(graph, timePeriod);
            }
        },

        showExerciseProblems: function(exercise) {
            this.showVitalStatistics("exercise-problems", exercise);
        },

        showVitalStatisticsForTimePeriod: function(graph, timePeriod) {
            this.showVitalStatistics(graph, null, timePeriod);
            $(".vital-statistics-description ." + graph + " ." + timePeriod).addClass("selected")
                .siblings().removeClass("selected");
        },

        showAchievements: function() {
            $("#tab-content-achievements").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-achievements").attr("rel"));
            this.updateTitleBreadcrumbs(["Achievements"]);
        },

        showGoals: function(type) {
            type = type || "current";

            GoalProfileViewsCollection.showGoalType(type);

            $("#tab-content-goals").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-goals").attr("rel"));
            this.updateTitleBreadcrumbs(["Goals"]);
        },

        activateRelatedTab: function(rel) {
            $(".profile-navigation .vertical-tab-list a").removeClass("active-tab");
            $("a[rel$='" + rel + "']").addClass("active-tab");
        },

        /**
         * Updates the title of the profile page to show breadcrumbs
         * based on the parts in the specified array. Will always pre-pend the profile
         * nickname.
         * @param {Array.<string>} parts A list of strings that will be HTML-escaped
         *     to be the breadcrumbs.
         */
        updateTitleBreadcrumbs: function(parts) {
            var rootCrumb = Profile.profile.get("nickname") || "Profile";
            parts.unshift(rootCrumb);

            var sheetTitle = $(".profile-sheet-title");
            if (parts && parts.length) {
                sheetTitle.text(parts.join(" » "));
            } else {
                sheetTitle.text("");
            }
        }
    }),

    /**
     * Navigate the router appropriately,
     * either to change profile sheets or vital-stats time periods.
     */
    onNavigationElementClicked_: function(event) {
        // TODO: Make sure middle-click + windows control-click Do The Right Thing
        // in a reusable way
        if (!event.metaKey) {
            event.preventDefault();
            var route = $(this).attr("href").replace(
                    Profile.profileRoot, "");
            Profile.router.navigate(route, true);
        }
    },

    loadGraph: function(href) {
        var apiCallbacksTable = {
            "/api/v1/user/exercises": this.renderExercisesTable,
            "/api/v1/exercises": this.renderFakeExercisesTable_,
        };
        if (!href) {
            return;
        }

        if (this.fLoadingGraph) {
            setTimeout(function() {Profile.loadGraph(href);}, 200);
            return;
        }

        this.fLoadingGraph = true;
        this.fLoadedGraph = false;
        $(".graph-notification").html("");

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
                Profile.finishLoadGraph(data, apiCallback);
            },
            error: function() {
                Profile.finishLoadGraphError();
            }
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },

    finishLoadGraph: function(data, apiCallback) {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);

        var start = (new Date).getTime();
        if (apiCallback) {
            apiCallback(data);
        } else {
            $("#graph-content").html(data);
        }
        var diff = (new Date).getTime() - start;
        KAConsole.log("API call rendered in " + diff + " ms.");

        this.fLoadedGraph = true;
    },

    finishLoadGraphError: function() {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);
        $(".graph-notification").html("It's our fault. We ran into a problem loading this graph. Try again later, and if this continues to happen please <a href='/reportissue?type=Defect'>let us know</a>.")
    },

    renderFakeGraph: function(graphName, timePeriod) {
        if (graphName === "activity") {
            // TODO: Don't re-initialize unnecessarily
            new ActivityGraph().render(null, timePeriod);
            Profile.fLoadedGraph = true;
        } else if (graphName === "focus") {
            // TODO: Don't re-initialize unnecessarily
            new FocusGraph().render();
            Profile.fLoadedGraph = true;
        } else if (graphName === "exercise-progress") {
            Profile.loadGraph("/api/v1/exercises");
        }

        $(".graph-notification").html("Witty text that conveys ACLness in normal-people terms.");
    },

    generateFakeExerciseTableData_: function(exerciseData) {
        // Generate some vaguely plausible exercise progress data
        return _.map(exerciseData, function(exerciseModel) {
            // See models.py -- h_position corresponds to the node's vertical position
            var position = exerciseModel["h_position"],
                totalDone = 0,
                states = {},
                rand = Math.random();
            if (position < 10) {
                if (Math.random() < 0.9) {
                    totalDone = 1;
                    if (rand < 0.5) {
                        states["proficient"] = true;
                    } else if (rand < 0.7) {
                        states["reviewing"] = true
                    }
                }
            } else if (position < 17) {
                if (Math.random() < 0.6) {
                    totalDone = 1;
                    if (rand < 0.4) {
                        states["proficient"] = true;
                    } else if (rand < 0.7) {
                        states["reviewing"] = true;
                    } else if (rand < 0.75) {
                        states["struggling"] = true;
                    }
                }
            } else {
                if (Math.random() < 0.1) {
                    totalDone = 1;
                    if (rand < 0.2) {
                        states["proficient"] = true;
                    } else if (rand < 0.5) {
                        states["struggling"] = true;
                    }
                }
            }
            return {
                "exercise_model": exerciseModel,
                "total_done": totalDone,
                "exercise_states": states
            }
        });
    },

    renderFakeExercisesTable_: function(exerciseData) {
        // Do nothing if the user switches sheets before /api/v1/exercises responds
        // (The other fake sheets are rendered randomly client-side)

        if (Profile.fLoadedGraph) {
            return;
        }

        var fakeData = Profile.generateFakeExerciseTableData_(exerciseData);

        Profile.renderExercisesTable(fakeData, false);

        $("#module-progress").addClass("empty-chart");
    },

    /**
     * Renders the exercise blocks given the JSON blob about the exercises.
     */
    renderExercisesTable: function(data, bindEvents) {
        var templateContext = [],
            bindEvents = (bindEvents === undefined) ? true : bindEvents,
            isEmpty = true,
            exerciseModels = [];
        

        for (var i = 0, exercise; exercise = data[i]; i++) {
            var stat = "Not started";
            var color = "";
            var states = exercise["exercise_states"];
            var totalDone = exercise["total_done"];

            if (totalDone > 0) {
                isEmpty = false;
            }

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
            exerciseModels.push(model);
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

        // TODO: Update API in v2 to send whether graph is empty, like others?
        if (isEmpty) {
            Profile.renderFakeExercisesTable_(exerciseModels);
            $(".graph-notification").html("This chart doesn't have any progress to show. " +
                    "Go <a href='/#browse'>watch some videos</a> and " +
                    "<a href='/exercisedashboard'>do some exercises</a>!");
            return;
        }
        var template = Templates.get("profile.exercise_progress");
        $("#graph-content").html(template({ "exercises": templateContext }));

        if (bindEvents) {
            Profile.hoverContent($("#module-progress .student-module-status"));
            $("#module-progress .student-module-status").click(function(e) {
                $("#info-hover-container").hide();
                // Extract the name from the ID, which has been prefixed.
                var exerciseName = this.id.substring("exercise-".length);
                Profile.router.navigate("/vital-statistics/exercise-problems/" + exerciseName, true);
            });
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
        Handlebars.registerHelper("graph-date-picker-wrapper", function(block) {
            this.graph = block.hash.graph;
            return block(this);
        });
        Handlebars.registerPartial("graph-date-picker", Templates.get("profile.graph-date-picker"));
        Handlebars.registerPartial("vital-statistics", Templates.get("profile.vital-statistics"));

        $("#profile-content").html(profileTemplate({
            profileRoot: this.profileRoot,
            profileData: this.profile.toJSON()
        }));

        // Show only the user card tab,
        // since the Backbone default route isn't triggered
        // when visiting khanacademy.org/profile
        $("#tab-content-user-profile").show().siblings().hide();

        Profile.populateUserCard();
        Profile.populateAchievements();
        Profile.populateGoals();

        // TODO: Might there be a better way
        // for server-side + client-side to co-exist in harmony?
        $("#tab-content-user-profile").append($("#server-side-recent-activity").html());

        this.profile.bind("change:nickname", function(profile) {
            var nickname = profile.get("nickname") || "Profile";
            $("#profile-tab-link").text(nickname);
            $("#top-header-links .user-name a").text(nickname);
        });
        this.profile.bind("change:avatarSrc", function(profile) {
            $(".profile-tab-avatar").attr("src", profile.get("avatarSrc"));
        });
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

                if (Profile.profile.isEditable()) {
                    // The display-case is only editable if you're viewing your
                    // own profile

                    // TODO: save and cache these objects
                    var fullBadgeList = new Badges.UserBadgeList();

                    var collection = data["badgeCollections"];
                    $.each(collection, function(i, categoryJson) {
                        $.each(categoryJson["userBadges"], function(j, json) {
                            fullBadgeList.add(new Badges.UserBadge(json));
                        });
                    });
                    displayCase.setFullBadgeList(fullBadgeList);
                }

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
                $("#profile-achievements-content").html(achievementsTemplate(data));

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

                // Start with meteorite badges displayed
                $("#category-0").click();
                $("abbr.timeago").timeago();

                // TODO: move into profile-goals.js?
                var currentGoals = window.GoalBook.map(function(g) { return g.get("title"); });
                _($(".add-goal")).map(function(elt) {
                    var button = $(elt);
                    var badge = button.closest(".achievement-badge");
                    var goalTitle = badge.find(".achievement-title").text();

                    // remove +goal button if present in list of active goals
                    if (_.indexOf(currentGoals, goalTitle) > -1) {

                        button.remove();

                    // add +goal behavior to button, once.
                    } else {
                        button.one("click", function() {
                            var goalObjectives = _(badge.data("objectives")).map(function(exercise) {
                                return {
                                    "type" : "GoalObjectiveExerciseProficiency",
                                    "internal_id" : exercise
                                };
                            });

                            var goal = new Goal({
                                title: goalTitle,
                                objectives: goalObjectives
                            });

                            window.GoalBook.add(goal);

                            goal.save()
                                .fail(function(err) {
                                    var error = err.responseText;
                                    button.addClass("failure")
                                        .text("oh no!").attr("title", "This goal could not be saved.");
                                    KAConsole.log("Error while saving new badge goal", goal);
                                    window.GoalBook.remove(goal);
                                })
                                .success(function() {
                                    button.text("Goal Added!").addClass("success");
                                    badge.find(".energy-points-badge").addClass("goal-added");
                                });
                        });
                    }
                });
            }
        });
    },

    populateGoals: function() {
        // TODO: Abstract away profile + actor privileges?
        var email = Profile.profile.get("email");
        if (email) {
            $.ajax({
                type: "GET",
                url: "/api/v1/user/goals",
                data: {email: email},
                dataType: "json",
                success: function(data) {
                    GoalProfileViewsCollection.render(data);
                }
            });
        } else {
            Profile.renderFakeGoals_();
        }
    },

    renderFakeGoals_: function() {
        var exerciseGoal = new Goal(Goal.defaultExerciseProcessGoalAttrs_),
            videoGoal = new Goal(Goal.defaultVideoProcessGoalAttrs_),
            fakeGoalBook = new GoalCollection([exerciseGoal, videoGoal]),
            fakeView = new GoalProfileView({model: fakeGoalBook}),
            jelNotification = $('<div class="graph-notification">' +
                    'Witty text that conveys ACLness in normal-people terms.</div>');

        // TODO: Unify the notification code, tend to the look + feel
        // Either need to cover up the goals or actually make them unclickable/unhoverable
        $("#profile-goals-content").append(jelNotification)
            .append(fakeView.show().addClass("empty-chart"));
    }
};
