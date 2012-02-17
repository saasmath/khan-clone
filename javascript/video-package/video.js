
var Video = {

    SHOW_SUBTITLES_COOKIE: 'show_subtitles',

    waitingForVideo: null,

    init: function() {

        this.router = new VideoRouter();

        Backbone.history.start({pushState: true, root: "/" + videoTopLevelTopic});

        this.rootLength = 1 + videoTopLevelTopic.length;

        VideoControls.onYouTubeBlocked(function() {

           $("#youtube_blocked").css("visibility", "visible").css("left", "0px").css("position", "relative");
           $("#idOVideo").hide();
           VideoStats.prepareAlternativePlayer(); // If YouTube is hidden, use the flv player for statistics

        });

    },

    renderPage: function(topicData, videoData) {
        var self = this;
        var navTemplate = Templates.get("video.video-nav");
        var descTemplate = Templates.get("video.video-description");
        var headerTemplate = Templates.get("video.video-header");
        var footerTemplate = Templates.get("video.video-footer");

        // Fix up data for templating
        if (videoData.related_exercises &&
            videoData.related_exercises.length) {
            videoData.related_exercises[videoData.related_exercises.length - 1].last = true;
        }

        // Render HTML
        $("div.video").show();
        $("span.video-nav").html(navTemplate({topic: topicData.topic, video: videoData}));
        $(".video-title").html(videoData.title);
        $("div.video-description").html(descTemplate({topic: topicData.topic, video: videoData}));
        $("span.video-header").html(headerTemplate({topic: topicData.topic, video: videoData}));
        $("span.video-footer").html(footerTemplate({topic: topicData.topic, video: videoData}));

        document.title = videoData.title + " | " + topicData.topic.title + " | Khan Academy";

        var jVideoDropdown = $('#video_dropdown');
        if ( jVideoDropdown.length ) {
            jVideoDropdown.css('display', 'inline-block');

            var menu = $('#video_dropdown ol').menu();
            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css('position', 'absolute');
            menu.bind("menuselect", function(e, ui){
                var fragment = ui.item.children('a').attr('href').substr(self.rootLength);
                Video.router.navigate(fragment, {trigger: true});
            });
            $(document).bind("click focusin", function(e){
                if ($(e.target).closest("#video_dropdown").length == 0) {
                    menu.hide();
                }
            });

            var button = $('#video_dropdown > a').button({
                icons: {
                    secondary: 'ui-icon-triangle-1-s'
                }
            }).show().click(function(e){
                if (menu.css('display') == 'none')
                    menu.show().menu("activate", e, $('#video_dropdown li[data-selected=selected]')).focus();
                else
                    menu.hide();
                e.preventDefault();
            });
        }

        $('.and-more').click(function(){
            $(this).hide();
            $('.more-content').show();
            return false;
        });

        $('.subtitles-link').click(function() { Video.toggleSubtitles(); return false; });
        if (readCookie(this.SHOW_SUBTITLES_COOKIE))
            this.showSubtitles();


        $('.sharepop').hide();

        $('.share-link').click(function() {
            $(this).next(".sharepop").toggle("drop",{direction:'up'},"fast");
            return false;
        });

        // If the user starts writing feedback, disable autoplay.
        $("span.video-footer").on("focus keydown", "input,textarea", function(event) {
            VideoControls.setAutoPlayEnabled(false);
        });

        VideoControls.playVideo(videoData.youtube_id, videoData.key, false);

        // Start up various scripts
        Discussion.init();
        Moderation.init();
        Voting.init();
        Comments.init();
        QA.init();

        // We take the message in the title of the energy points box and place it
        // in a tooltip, and if it's the message with a link to the login we
        // replace it with a nicer link (we don't want to have to pass the url to
        // the templatetag).
        var $points = $(".video-energy-points");
        $points.data("title", $points.attr("title").replace(/Sign in/,
                   "<a href=\"" + loginURL + "\">Sign in</a>"))
               .removeAttr("title");

        VideoStats.tooltip("#points-badge-hover", $points.data("title"));

        // Set up next/previous links
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

    loadVideo: function(topic, video) {
        var descTemplate = Templates.get("video.video-description");
        var waitingForVideo = (Video.waitingForVideo && 
            Video.waitingForVideo.topic == topic &&
            Video.waitingForVideo.video == video);

        if (videoLibrary[topic] && videoLibrary[topic].videos[video]) {
            if (waitingForVideo) {
                if (videoLibrary[topic].videos[video] !== "LOADING") {
                    KAConsole.log("Switching to video: " + video + " in topic " + topic);
                    Video.renderPage(videoLibrary[topic], videoLibrary[topic].videos[video]);
                    return; // No longer waiting
                }
            } else {
                return; // Nothing to do
            }
        } else {
            KAConsole.log("Loading video: " + video + " in topic " + topic);
            url = "/api/v1/videos/" + topic + "/" + video + "/play" + (videoLibrary[topic] ? "" : "?topic=1");

            videoLibrary[topic] = videoLibrary[topic] || { videos: [] };
            videoLibrary[topic].videos[video] = "LOADING";

            $.ajax({
                url: url,
                success: function(json) {
                    var waitingForVideo = (Video.waitingForVideo && 
                        Video.waitingForVideo.topic == topic &&
                        Video.waitingForVideo.video == video);
                    if (json.topic)
                        videoLibrary[topic].topic = json.topic;
                    videoLibrary[topic].videos[video] = json.video;
                    if (waitingForVideo) {
                        KAConsole.log("Switching to video: " + video + " in topic " + topic);
                        Video.renderPage(videoLibrary[topic], json.video);
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
        if ($('.subtitles-warning').is(":visible"))
            this.hideSubtitles();
        else
            this.showSubtitles();
    },


    hideSubtitles: function() {
        eraseCookie(this.SHOW_SUBTITLES_COOKIE);
        Video.hideSubtitleElements();
    },

    hideSubtitleElements: function() {
        $('.unisubs-videoTab').hide();
        $('.subtitles-warning').hide();
        $('.youtube-video').css('marginBottom', '0px');
        Throbber.hide();
    },

    showSubtitleElements: function() {
        $('.youtube-video').css('marginBottom', '32px');
        $('.subtitles-warning').show();
        $('.unisubs-videoTab').show();
    },

    showSubtitles: function() {
        createCookie(this.SHOW_SUBTITLES_COOKIE, true, 365);
        Video.showSubtitleElements();

        if ($('.unisubs-videoTab').length == 0)
        {
            setTimeout(function() {
                Throbber.show($(".subtitles-warning"), true);
            }, 1);

            $.getScript('http://s3.www.universalsubtitles.org/js/mirosubs-widgetizer.js', function() {
                // Workaround bug where subtitles are not displayed if video was already playing until
                // video is paused and restarted.  We wait 3 secs to give subtitles a chance to load.
                setTimeout(function() {
                    if (VideoControls.player && VideoControls.player.getPlayerState() == 1 /* playing */)
                    {
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
        if (path.charAt(0) == "/") {
            path = path.substr(1);
        }
        pathList = [videoTopLevelTopic].concat(path.split("/"));
        if (pathList.length >= 3) {
            var video = pathList[pathList.length-1];
            var topic = pathList[pathList.length-3];

            Video.waitingForVideo = { topic: topic, video: video };
            Video.loadVideo(topic, video);
        } else {
            $("div.video").hide();
        }
    }
});

