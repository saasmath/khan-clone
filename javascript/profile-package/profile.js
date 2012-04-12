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

    /**
     * The root segment of the URL for the profile page for this user.
     * Will be of the form "/profile/<identifier>" where identifier
     * can be a username, or other identifier sent by the server.
     */
    profileRoot: "",

    /**
     * Whether or not we can collect sensitive information like the user's
     * name. Users under 13 without parental consent should not be able
     * to enter data.
     */
    isDataCollectible: false,

    /**
     * Overridden w profile-intro.js if necessary
     */
    showIntro_: function() {},

    /**
     * Called to initialize the profile page. Passed in with JSON information
     * rendered from the server. See templates/viewprofile.html for details.
     */
    init: function(json) {
        this.profile = new ProfileModel(json.profileData);
        this.profile.bind("savesuccess", this.onProfileUpdated_, this);

        var root = json.profileRoot;
        if (window.location.pathname.indexOf("@") > -1) {
            // Note the path should be encoded so that @ turns to %40. However,
            // there is a bug (https://bugs.webkit.org/show_bug.cgi?id=30225)
            // that makes Safari always return the decoded part. Also, if
            // the user manually types in an @ sign, it will be returned
            // decoded. So we need to be robust to this.
            root = decodeURIComponent(root);
        }

        this.profileRoot = root;
        this.isDataCollectible = json.isDataCollectible;
        this.secureUrlBase = json.secureUrlBase;
        UserCardView.countVideos = json.countVideos;
        UserCardView.countExercises = json.countExercises;

        Profile.render();

        Profile.router = new Profile.TabRouter({routes: this.getRoutes_()});
        Profile.router.bind("all", Analytics.handleRouterNavigation);

        Backbone.history.start({
            pushState: true,
            root: this.profileRoot
        });

        Profile.showIntro_();

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

        var navElementHandler = _.bind(this.onNavigationElementClicked_, this);
        // Delegate clicks for tab navigation
        $(".profile-navigation .vertical-tab-list").delegate("a",
                "click", navElementHandler);

        // Delegate clicks for vital statistics time period navigation
        $("#tab-content-vital-statistics").delegate(".graph-date-picker a",
                "click", navElementHandler);

        $("#tab-content-goals").delegate(".graph-picker .type a",
                "click", navElementHandler);

        // Delegate clicks for recent badge-related activity
        $(".achievement .ach-text").delegate("a", "click", function(event) {
            if (!event.metaKey) {
                event.preventDefault();
                Profile.router.navigate("achievements", true);
                $("#achievement-list ul li#category-" + $(this).data("category")).click();
            }
        });
    },

    /**
     * All the tabs that you could encounter on the profile page.
     */
    subRoutes: {
        "achievements": "showAchievements",
        "goals/:type": "showGoals",
        "goals": "showGoals",
        "vital-statistics": "showVitalStatistics",
        "vital-statistics/problems/:exercise": "showExerciseProblems",
        "vital-statistics/:graph/:timePeriod": "showVitalStatisticsForTimePeriod",
        "vital-statistics/:graph": "showVitalStatistics",
        "coaches": "showCoaches",
        "discussion": "showDiscussion",
        // Not associated with any tab highlighting.
        "settings": "showSettings",

        "": "showDefault",
        // If the user types /profile/username/ with a trailing slash
        // it should work, too
        "/": "showDefault",

        // If any old or crazy vital-statistics route is passed that we no longer support
        // and therefore hasn't matched yet, just show the default vital statistics graph.
        "vital-statistics/*path": "showVitalStatistics",

        // A minor hack to ensure that if the user navigates to /profile without
        // her username, it still shows the default profile screen. Note that
        // these routes aren't relative to the root URL, but will still work.
        "profile": "showDefault",
        "profile/": "showDefault",
        // And for the mobile app... hopefully we can find a better fix.
        "profile?view=mobile": "showDefault"
    },

    /**
     * Generate routes hash to be used by Profile.router
     */
    getRoutes_: function() {
        return this.subRoutes;
    },

    /**
     * Handle a change to the profile root.
     */
    onProfileUpdated_: function() {
        var username = this.profile.get("username");
        if (username && Profile.profileRoot != ("/profile/" + username + "/")) {
            // Profile root changed - we need to reload the page since
            // Backbone.router isn't happy when the root changes.
            window.location.replace("/profile/" + username + "/");
        }
    },

    TabRouter: Backbone.Router.extend({
        showDefault: function() {
            Profile.populateActivity().then(function() {
                // Pre-fetch badges, after the activity has been loaded, since
                // they're needed to edit the display-case.
                if (Profile.profile.isEditable()) {
                    Profile.populateAchievements();
                }
            });
            $("#tab-content-user-profile").show().siblings().hide();
            this.activateRelatedTab($("#tab-content-user-profile").attr("rel"));
            this.updateTitleBreadcrumbs();
        },

        showVitalStatistics: function(graph, exercise, timePeriod) {
            var exercise = exercise || "addition_1",
                emailEncoded = encodeURIComponent(USER_EMAIL),
                hrefLookup = {
                    "activity": "/profile/graph/activity?student_email=" + emailEncoded,
                    "focus": "/profile/graph/focus?student_email=" + emailEncoded,
                    "skill-progress-over-time": "/profile/graph/exercisesovertime?student_email=" + emailEncoded,
                    "skill-progress": "/api/v1/user/exercises?email=" + emailEncoded,
                    "problems": "/profile/graph/exerciseproblems?" +
                                            "exercise_name=" + exercise +
                                            "&" + "student_email=" + emailEncoded
                },
                timePeriodLookup = {
                    "today": "&dt_start=today",
                    "yesterday": "&dt_start=yesterday",
                    "last-week": "&dt_start=lastweek&dt_end=today",
                    "last-month": "&dt_start=lastmonth&dt_end=today"
                },
                graph = !!(hrefLookup[graph]) ? graph : "activity",
                timePeriod = !!(timePeriodLookup[timePeriod]) ? timePeriod : "last-week",
                timeURLParameter = timePeriodLookup[timePeriod],
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
            if (graph == "problems") {
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
            this.showVitalStatistics("problems", exercise);
        },

        showVitalStatisticsForTimePeriod: function(graph, timePeriod) {
            this.showVitalStatistics(graph, null, timePeriod);
            $(".vital-statistics-description ." + graph + " ." + timePeriod).addClass("selected")
                .siblings().removeClass("selected");
        },

        showAchievements: function() {
            Profile.populateAchievements();
            $("#tab-content-achievements").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-achievements").attr("rel"));
            this.updateTitleBreadcrumbs(["Achievements"]);
        },

        showGoals: function(type) {
            type = type || "current";
            Profile.populateGoals();

            GoalProfileViewsCollection.showGoalType(type);

            $("#tab-content-goals").show()
                .siblings().hide();
            this.activateRelatedTab($("#tab-content-goals").attr("rel"));
            this.updateTitleBreadcrumbs(["Goals"]);
        },

        showCoaches: function() {
            Profile.populateCoaches();

            $("#tab-content-coaches").show()
                .siblings().hide();

            this.activateRelatedTab("community coaches");
            this.updateTitleBreadcrumbs(["Coaches"]);

            if (Profile.profile.get("isPhantom")) {
                Profile.showNotification("no-coaches-for-phantoms");
            }
        },

        showDiscussion: function() {
            $("#tab-content-discussion").show()
                .siblings().hide();

            this.activateRelatedTab("community discussion");
            this.updateTitleBreadcrumbs(["Discussion"]);

            Profile.populateDiscussion();
        },

        settingsIframe_: null,
        showSettings: function() {
            // Password change forms need to happen in an iframe since it needs
            // to be POST'ed to a different domain (with https), and redirected
            // back with information on error/success.
            if (!Profile.settingsIframe_) {
                Profile.settingsIframe_ = $("<iframe></iframe>")
                        .attr("src", "/pwchange")
                        .attr("frameborder", "0")
                        .attr("scrolling", "no")
                        .attr("allowtransparency", "yes")
                        .attr("id", "settings-iframe")
                        .attr("class", "settings-iframe")
                        .appendTo($("#tab-content-settings"));
            }

            // Show.
            $("#tab-content-settings").show().siblings().hide();
            this.activateRelatedTab("");
            this.updateTitleBreadcrumbs(["Settings"]);
        },

        activateRelatedTab: function(rel) {
            $(".profile-navigation .vertical-tab-list a").removeClass("active-tab");
            $("a[rel='" + rel + "']").addClass("active-tab");
        },

        /**
         * Updates the title of the profile page to show breadcrumbs
         * based on the parts in the specified array. Will always pre-pend the profile
         * nickname.
         * @param {Array.<string>} parts A list of strings that will be HTML-escaped
         *     to be the breadcrumbs.
         */
        updateTitleBreadcrumbs: function(parts) {
            $(".profile-notification").hide();

            var sheetTitle = $(".profile-sheet-title");
            if (parts && parts.length) {
                var rootCrumb = Profile.profile.get("nickname") || "Profile";
                parts.unshift(rootCrumb);
                sheetTitle.text(parts.join(" » ")).show();

                if (!Profile.profile.get("email")) {
                    $(".profile-notification").show();
                }
            } else {
                sheetTitle.text("").hide();
            }
        }
    }),

    /**
     * Navigate the router appropriately,
     * either to change profile sheets or vital-stats time periods.
     */
    onNavigationElementClicked_: function(e) {
        // TODO: Make sure middle-click + windows control-click Do The Right Thing
        // in a reusable way
        if (!e.metaKey) {
            e.preventDefault();
            var route = $(e.currentTarget).attr("href");
            // The navigation elements have the profileRoot in the href, but
            // Router.navigate should be relative to the root.
            if (route.indexOf(this.profileRoot) === 0) {
                route = route.substring(this.profileRoot.length);
            }
            Profile.router.navigate(route, true);
        }
    },

    loadGraph: function(href) {
        var apiCallbacksTable = {
            "/api/v1/user/exercises": this.renderExercisesTable,
            "/api/v1/exercises": this.renderFakeExercisesTable_
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
        Profile.showNotification("error-graph");
    },

    renderFakeGraph: function(graphName, timePeriod) {
        if (graphName === "activity") {
            ActivityGraph.render(null, timePeriod);
            Profile.fLoadedGraph = true;
        } else if (graphName === "focus") {
            FocusGraph.render();
            Profile.fLoadedGraph = true;
        } else if (graphName === "skill-progress") {
            Profile.loadGraph("/api/v1/exercises");
        } else {
            ExerciseGraphOverTime.render();
            Profile.fLoadedGraph = true;
        }
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
                        states["reviewing"] = true;
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
            };
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

        if (isEmpty) {
            Profile.renderFakeExercisesTable_(exerciseModels);
            Profile.showNotification("empty-graph");
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
                Profile.router.navigate("vital-statistics/problems/" + exerciseName, true);
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

    /**
     * Show a profile notification
     * Expects the class name of the div to show, such as "error-graph"
     */
    showNotification: function(className) {
        var jel = $(".profile-notification").removeClass("uncover-nav");

        if (className === "empty-graph" || className === "no-discussion") {
            jel.addClass("uncover-nav");
        }

        jel.show()
            .find("." + className).show()
            .siblings().hide();
    },

    hoverContent: function(elements, containerSelector) {
        var lastHoverTime,
            mouseX,
            mouseY;

        containerSelector = containerSelector || "#graph-content";

        elements.hover(
            function(e) {
                var hoverTime = +(new Date()),
                    el = this;
                lastHoverTime = hoverTime;
                mouseX = e.pageX;
                mouseY = e.pageY;

                setTimeout(function() {
                    if (hoverTime !== lastHoverTime) {
                        return;
                    }

                    var hoverData = $(el).children(".hover-data"),
                        html = $.trim(hoverData.html());

                    if (html) {
                        var jelContainer = $(containerSelector),
                            leftMax = jelContainer.offset().left + jelContainer.width() - 150,
                            left = Math.min(mouseX + 15, leftMax),
                            jHoverEl = $("#info-hover-container");

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
            profileData: this.profile.toJSON(),
            countVideos: UserCardView.countVideos,
            countExercises: UserCardView.countExercises
        }));

        // Show only the user card tab,
        // since the Backbone default route isn't triggered
        // when visiting khanacademy.org/profile
        $("#tab-content-user-profile").show().siblings().hide();

        Profile.populateUserCard();

        this.profile.bind("change:nickname", function(profile) {
            var nickname = profile.get("nickname") || "Profile";
            $("#profile-tab-link").text(nickname);
            $("#top-header-links .user-name a").text(nickname);
        });
        this.profile.bind("change:avatarSrc", function(profile) {
            var src = profile.get("avatarSrc");
            $(".profile-tab-avatar").attr("src", src);
            $("#top-header #user-info .user-avatar").attr("src", src);
        });
    },

    userCardPopulated_: false,
    populateUserCard: function() {
        if (Profile.userCardPopulated_) {
            return;
        }
        var view = new UserCardView({model: this.profile});
        $(".user-info-container").html(view.render().el);

        var publicBadgeList = new Badges.BadgeList(
                this.profile.get("publicBadges"));
        publicBadgeList.setSaveUrl("/api/v1/user/badges/public");
        var displayCase = new Badges.DisplayCase({ model: publicBadgeList });
        $(".sticker-book").append(displayCase.render().el);
        Profile.displayCase = displayCase;

        Profile.userCardPopulated_ = true;
    },

    achievementsDeferred_: null,
    populateAchievements: function() {
        if (Profile.achievementsDeferred_) {
            return Profile.achievementsDeferred_;
        }
        // Asynchronously load the full badge information in the background.
        return Profile.achievementsDeferred_ = $.ajax({
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
                    Profile.displayCase.setFullBadgeList(fullBadgeList);
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

                // Start with meteorite badges displayed
                $("#category-0").click();

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

    goalsDeferred_: null,
    populateGoals: function() {
        if (Profile.goalsDeferred_) {
            return Profile.goalsDeferred_;
        }

        // TODO: Abstract away profile + actor privileges
        // Also in profile.handlebars
        var email = Profile.profile.get("email");
        if (email) {
            Profile.goalsDeferred_ = $.ajax({
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
            Profile.goalsDeferred_ = new $.Deferred();
            Profile.goalsDeferred_.resolve();
        }
        return Profile.goalsDeferred_;
    },

    renderFakeGoals_: function() {
        var exerciseGoal = new Goal(Goal.defaultExerciseProcessGoalAttrs_),
            videoGoal = new Goal(Goal.defaultVideoProcessGoalAttrs_),
            fakeGoalBook = new GoalCollection([exerciseGoal, videoGoal]),
            fakeView = new GoalProfileView({model: fakeGoalBook});

        $("#profile-goals-content").append(fakeView.show().addClass("empty-chart"));
    },

    coachesDeferred_: null,
    populateCoaches: function() {
        if (Profile.coachesDeferred_) {
            return Profile.coachesDeferred_;
        }

        Profile.coachesDeferred_ = Coaches.init();

        return Profile.coachesDeferred_;
    },

    discussionDeferred_: null,
    noDiscussion_: false,
    populateDiscussion: function() {
        if (Profile.noDiscussion_) {
            Profile.showNotification("no-discussion");
        }

        if (Profile.discussionDeferred_) {
            return Profile.discussionDeferred_;
        }

        var email = Profile.profile.get("email");
        if (email) {
            Profile.discussionDeferred_ = $.ajax({
                type: "GET",
                url: "/api/v1/user/questions",
                data: {
                    email: email,
                    casing: "camel"
                },
                dataType: "json",
                success: function(data) {
                    if (data.length === 0) {
                        Profile.noDiscussion_ = true;
                        Profile.showNotification("no-discussion");
                        return;
                    }

                    var template = Templates.get("profile.questions-list");

                    // Order questions from oldest to newest
                    data = _.sortBy(data, function(question) {
                        return question["lastDate"];
                    });

                    // Then reverse to get newest to oldest
                    data.reverse();

                    $("#tab-content-discussion")
                        .append(template(data))
                        .find("div.timeago").timeago();

                    var jelUnread = $("#tab-content-discussion").find(".unread");
                    if (Profile.profile.get("isSelf") && jelUnread.length !== 0) {
                        // TODO(marcia): Polish below

                        // Fade out notification in top-header
                        $("#top-header .notification-bubble")
                            .fadeOut(500, function() {
                                $("#top-header .user-notification img")
                                    .attr("src", "/images/discussions-lo-16px.png")
                            });

                        // Reset notifications count upon viewing this tab
                        $.ajax({
                            type: "PUT",
                            url: "/api/v1/user/reset_notifications_count"
                        });
                    }
                }
            });
        } else {
            Profile.discussionDeferred_ = new $.Deferred();
            Profile.discussionDeferred_.resolve();
        }

        return Profile.discussionDeferred_;
    },

    populateSuggestedActivity: function(activities) {
        var suggestedTemplate = Templates.get("profile.suggested-activity");

        var attachProgress = function(activity) {
            activity.progress = activity.progress || 0;
        };
        _.each(activities["exercises"] || [], attachProgress);
        _.each(activities["videos"] || [], attachProgress);
        $("#suggested-activity").append(suggestedTemplate(activities));
    },

    populateRecentActivity: function(activities) {
        var listTemplate = Templates.get("profile.recent-activity-list"),
            exerciseTemplate = Templates.get("profile.recent-activity-exercise"),
            badgeTemplate = Templates.get("profile.recent-activity-badge"),
            videoTemplate = Templates.get("profile.recent-activity-video"),
            goalTemplate = Templates.get("profile.recent-activity-goal");

        Handlebars.registerHelper("renderActivity", function(activity) {
            _.extend(activity, {profileRoot: Profile.profileRoot});

            if (activity.sType === "Exercise") {
                return exerciseTemplate(activity);
            } else if (activity.sType === "Badge") {
                return badgeTemplate(activity);
            } else if (activity.sType === "Video") {
                return videoTemplate(activity);
            } else if (activity.sType === "Goal") {
                return goalTemplate(activity);
            }

            return "";
        });

        $("#recent-activity").append(listTemplate(activities))
            .find("span.timeago").timeago();
    },

    activityDeferred_: null,
    populateActivity: function() {
        if (Profile.activityDeferred_) {
            return Profile.activityDeferred_;
        }
        $("#recent-activity-progress-bar").progressbar({value: 100});

        // TODO: Abstract away profile + actor privileges
        var email = Profile.profile.get("email");
        if (email) {
            Profile.activityDeferred_ = $.ajax({
                type: "GET",
                url: "/api/v1/user/activity",
                data: {
                    email: email,
                    casing: "camel"
                },
                dataType: "json",
                success: function(data) {
                    $("#activity-loading-placeholder").fadeOut(
                            "slow", function() {
                                $(this).hide();
                            });
                    Profile.populateSuggestedActivity(data.suggested);
                    Profile.populateRecentActivity(data.recent);
                    $("#activity-contents").show();
                }
            });
        } else {
            Profile.activityDeferred_ = new $.Deferred();
            Profile.activityDeferred_.resolve();
        }
        return Profile.activityDeferred_;
    }
};
