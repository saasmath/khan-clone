
var Video = {

    SHOW_SUBTITLES_COOKIE: "show_subtitles",

    waitingForVideo: null,
    currentVideoPath: null,
    rendered: false,
    youtubeBlocked: false,
    pushStateDisabled: false,

    init: function(params) {
        var self = this;

        this.videoLibrary = params.videoLibrary || {};
        this.loginURL = params.loginURL;

        if (params.videoTopLevelTopic) {
            this.videoTopLevelTopic = params.videoTopLevelTopic;
            this.rootLength = 1 + params.videoTopLevelTopic.length;

            if (window.history && window.history.pushState && params.videoTopLevelTopic) {
                this.router = new VideoRouter();
                Backbone.history.start({pushState: true, root: "/" + params.videoTopLevelTopic});
            } else {
                this.pushStateDisabled = true;
                Video.navigateToVideo(window.location.pathname);
            }
        } else {
            // Used for modal video player
            this.initEventHandlers();
        }

        VideoControls.onYouTubeBlocked(function() {

           var flvPlayerTemplate = Templates.get("video.video-flv-player");
           $("#youtube_blocked")
                .css("visibility", "visible")
                .css("left", "0px")
                .css("position", "relative")
                .html(flvPlayerTemplate({ video_path: self.currentVideoPath }));
           $("#idOVideo").hide();
           VideoStats.prepareAlternativePlayer(); // If YouTube is hidden, use the flv player for statistics

           self.youtubeBlocked = true;
        });

    },

    renderPage: function(topicData, videoData) {
        var self = this;
        var navTemplate = Templates.get("video.video-nav");
        var descTemplate = Templates.get("video.video-description");
        var headerTemplate = Templates.get("video.video-header");
        var footerTemplate = Templates.get("video.video-footer");

        if (!this.rendered) {
            // Initial page load
            this.rendered = true;
        } else {
            // Subsequent page load; send Google Analytics data
            if (window._gaq) {
                _gaq.push(['_trackPageview', window.location.pathname]);
            }
        }

        // Bingo conversions for watching a video video
        gae_bingo.bingo(["struggling_videos_landing",
            "suggested_activity_videos_landing",
            "suggested_activity_videos_landing_binary"]);

        // Fix up data for templating
        if (videoData.related_exercises &&
            videoData.related_exercises.length) {
            videoData.related_exercises[videoData.related_exercises.length - 1].last = true;
        }

        // Render HTML
        $("span.video-nav").html(navTemplate({topic: topicData.topic, video: videoData}));
        $(".video-title").html(videoData.title);
        $("div.video-description").html(descTemplate({topic: topicData.topic, video: videoData}));
        $("span.video-header").html(headerTemplate({topic: topicData.topic, video: videoData}));
        $("span.video-footer").html(footerTemplate({topic: topicData.topic, video: videoData}));

        document.title = videoData.title + " | " + topicData.topic.title + " | Khan Academy";

        this.currentVideoPath = videoData.video_path;

        var jVideoDropdown = $('#video_dropdown');
        if ( jVideoDropdown.length ) {
            jVideoDropdown.css('display', 'inline-block');

            var menu = $("#video_dropdown ol").menu();
            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css('position', 'absolute');
            menu.bind("menuselect", function(e, ui){
                if (self.pushStateDisabled) {
                    window.location.replace(ui.item.children("a").attr("href"));
                } else {
                    var fragment = ui.item.children("a").attr("href").substr(self.rootLength);
                    Video.router.navigate(fragment, {trigger: true});
                }
            });
            $(document).bind("click focusin", function(e) {
                if ($(e.target).closest("#video_dropdown").length === 0) {
                    menu.hide();
                }
            });

            var button = $("#video_dropdown > a").button({
                icons: {
                    secondary: "ui-icon-triangle-1-s"
                }
            }).show().click(function(e) {
                if (menu.css("display") === "none") {
                    menu.show().menu(
                        "activate", e,
                        $("#video_dropdown li[data-selected=selected]")
                    ).focus();
                } else {
                    menu.hide();
                }
                e.preventDefault();
            });
        }

        // If the user starts writing feedback, disable autoplay.
        $("span.video-footer").on("focus keydown", "input,textarea", function(event) {
            VideoControls.setAutoPlayEnabled(false);
        });

        if (this.youtubeBlocked) {
           var flvPlayerTemplate = Templates.get("video.video-flv-player");
           $("#youtube_blocked").html(flvPlayerTemplate({ video_path: this.currentVideoPath }));
           VideoStats.prepareAlternativePlayer(); // If YouTube is hidden, use the flv player for statistics
        } else {
            VideoControls.playVideo(videoData.youtube_id, videoData.key, false);
        }

        // Start up various scripts
        Discussion.init();
        Moderation.init();
        Voting.init();
        Comments.init();
        QA.init();

        this.initEventHandlers();

        // Set up next/previous links
        if (!this.pushStateDisabled) {
            $("a.previous-video,a.next-video").click(function(event) {
                var fragment = $(this).attr("href").substr(self.rootLength);
                Video.router.navigate(fragment, {trigger: true});
                event.stopPropagation();
                return false;
            });

            if (videoData.next_video) {
                // Autoplay to the next video
                var nextVideoFragment = $("a.next-video").attr("href").substr(self.rootLength);
                VideoControls.setAutoPlayCallback(function() {
                    Video.router.navigate(nextVideoFragment, {trigger: true});
                });
            } else {
                // Don't autoplay to next video
                VideoControls.setAutoPlayCallback(null);
            }
        } else {
            // Autoplay is disabled if there is no pushState support
            VideoControls.setAutoPlayCallback(null);
        }

        VideoControls.initContinuousPlayLinks($("span.video-footer"));

        // Preload adjacent videos after 15 seconds
        setTimeout(function() {
            if (videoData.previous_video) {
                Video.loadVideo(topicData.topic.id, videoData.previous_video.readable_id);
            }
            if (videoData.next_video) {
                Video.loadVideo(topicData.topic.id, videoData.next_video.readable_id);
            }
        }, 15000);

        this.waitingForVideo = null;
    },

    initEventHandlers: function() {

        $(".and-more").click(function() {
            $(this).hide();
            $(".more-content").show();
            return false;
        });

        $(".subtitles-link").click(function() { Video.toggleSubtitles(); return false; });
        if (readCookie(this.SHOW_SUBTITLES_COOKIE)) {
            this.showSubtitles();
        }

        $(".sharepop").hide();
        $(".share-link").click(function() {
            $(this).next(".sharepop").toggle("drop", {direction: "up"},"fast");
            return false;
        });

        // We take the message in the title of the energy points box and place it
        // in a tooltip, and if it's the message with a link to the login we
        // replace it with a nicer link (we don't want to have to pass the url to
        // the templatetag).
        var $points = $(".video-energy-points");
        $points.data("title", $points.attr("title").replace(/Sign in/,
                   "<a href=\"" + this.loginURL + "\">Sign in</a>"))
               .removeAttr("title");

        VideoStats.tooltip("#points-badge-hover", $points.data("title"));
    },

    navigateToVideo: function(path) {
        if (path.charAt(0) == "/") {
            path = path.substr(1);
        }
        pathList = [this.videoTopLevelTopic].concat(path.split("/"));
        if (pathList.length >= 3) {
            var video = pathList[pathList.length-1];
            var topic = pathList[pathList.length-3];

            this.waitingForVideo = { topic: topic, video: video, url: "/" + this.videoTopLevelTopic + "/" + path };
            this.loadVideo(topic, video);
        }
    },

    loadVideo: function(topic, video) {
        var self = this;
        var descTemplate = Templates.get("video.video-description");
        var waitingForVideo = (Video.waitingForVideo && 
            Video.waitingForVideo.topic == topic &&
            Video.waitingForVideo.video == video);

        if (this.videoLibrary[topic] && this.videoLibrary[topic].videos[video]) {
            if (waitingForVideo) {
                if (this.videoLibrary[topic].videos[video] !== "LOADING") {
                    KAConsole.log("Switching to video: " + video + " in topic " + topic);
                    Video.renderPage(this.videoLibrary[topic], this.videoLibrary[topic].videos[video]);
                    return; // No longer waiting
                }
            } else {
                return; // Nothing to do
            }
        } else {
            KAConsole.log("Loading video: " + video + " in topic " + topic);
            url = "/api/v1/videos/" + topic + "/" + video + "/play" + (this.videoLibrary[topic] ? "" : "?topic=1");

            this.videoLibrary[topic] = this.videoLibrary[topic] || { videos: [] };
            this.videoLibrary[topic].videos[video] = "LOADING";

            $.ajax({
                url: url,
                success: function(json) {
                    var waitingForVideo = (Video.waitingForVideo && 
                        Video.waitingForVideo.topic == topic &&
                        Video.waitingForVideo.video == video);
                    if (json.topic)
                        self.videoLibrary[topic].topic = json.topic;
                    self.videoLibrary[topic].videos[video] = json.video;
                    if (waitingForVideo) {
                        KAConsole.log("Switching to video: " + video + " in topic " + topic);
                        Video.renderPage(self.videoLibrary[topic], json.video);
                    }
                },
                error: function() {
                    var waitingForVideo = (Video.waitingForVideo && 
                        Video.waitingForVideo.topic == topic &&
                        Video.waitingForVideo.video == video);
                    if (waitingForVideo) {
                        window.location.assign(Video.waitingForVideo.url);
                    }
                }
            });
        }
        
        if (waitingForVideo) {
            $("span.video-nav").html("");
            $("div.video-description").html(descTemplate({video: { title: "Loading..." }, loading: true }));
            $("span.video-header").html("");
            $("span.video-footer").html("");
        }
    },

    toggleSubtitles: function() {
        if ($(".subtitles-warning").is(":visible")) {
            this.hideSubtitles();
        } else {
            this.showSubtitles();
        }
    },


    hideSubtitles: function() {
        eraseCookie(this.SHOW_SUBTITLES_COOKIE);
        Video.hideSubtitleElements();
    },

    hideSubtitleElements: function() {
        $(".unisubs-videoTab").css("display", "none !important");
        $(".subtitles-warning").hide();
        $(".youtube-video").css("marginBottom", "0px");
        Throbber.hide();
    },

    showSubtitleElements: function() {
        $(".youtube-video").css("marginBottom", "32px");
        $(".subtitles-warning").show();
        // 2012-02-23: unisubs uses !important in their styles, forcing us to
        // follow along when showing and hiding their tab.
        $(".unisubs-videoTab").css("display", "block !important");
    },

    showSubtitles: function() {
        createCookie(this.SHOW_SUBTITLES_COOKIE, true, 365);
        Video.showSubtitleElements();

        if ($(".unisubs-videoTab").length === 0) {
            window.setTimeout(function() {
                Throbber.show($(".subtitles-warning"), true);
            }, 1);

            $.getScript("http://s3.www.universalsubtitles.org/js/mirosubs-widgetizer.js", function() {
                // Workaround bug where subtitles are not displayed if video was already playing until
                // video is paused and restarted.  We wait 3 secs to give subtitles a chance to load.
                window.setTimeout(function() {
                    if (VideoControls.player &&
                            VideoControls.player.getPlayerState() === 1 /* playing */) {
                        VideoControls.pause();
                        VideoControls.play();
                    }
                }, 3000);
            });
        }
    }
};

window.VideoRouter = Backbone.Router.extend({
    routes: {
        "*path": "video"
    },

    video: function(path) {
        Video.navigateToVideo(path);
    }
});

