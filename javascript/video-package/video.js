
var Video = {

    SHOW_SUBTITLES_COOKIE: 'show_subtitles',

    waitingForVideo: null,

    init: function() {

        this.router = new VideoRouter();

        Backbone.history.start({pushState: true, root: "/video/"});

        VideoControls.onYouTubeBlocked(function() {

           $("#youtube_blocked").css("visibility", "visible").css("left", "0px").css("position", "relative");
           $("#idOVideo").hide();
           VideoStats.prepareAlternativePlayer(); // If YouTube is hidden, use the flv player for statistics

        });

        var jVideoDropdown = $('#video_dropdown');
        if ( jVideoDropdown.length ) {
            jVideoDropdown.css('display', 'inline-block');

            var menu = $('#video_dropdown ol').menu();
            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css('position', 'absolute');
            menu.bind("menuselect", function(e, ui){
                window.location.href = ui.item.children('a').attr('href');
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

    },

    renderPage: function(videoData) {
        var navTemplate = Templates.get("video.video-nav");
        var descTemplate = Templates.get("video.video-description");
        var contentTemplate = Templates.get("video.video-content");

        // Fix up data for templating
        if (videoData.related_exercises &&
            videoData.related_exercises.length) {
            videoData.related_exercises[videoData.related_exercises.length - 1].last = true;
        }

        // Render HTML
        $("span.video-nav").html(navTemplate(videoData));
        $(".video-title").html(videoData.video.title);
        $("div.video-description").html(descTemplate(videoData));
        $("span.video-content").html(contentTemplate(videoData));


        // Start up various scripts
        VideoStats.startLoggingProgress(videoData.video_key);
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

        var previousVideoTopic = (videoData.previous_video_topic ? videoData.previous_video_topic.id : videoData.topic.id);
        var previousVideoFragment = videoData.previous_video.readable_id + "?topic=" + previousVideoTopic;

        var nextVideoTopic = (videoData.next_video_topic ? videoData.next_video_topic.id : videoData.topic.id);
        var nextVideoFragment = videoData.next_video.readable_id + "?topic=" + nextVideoTopic;

        // Set up next/previous links
        $("a.previous-video").click(function(event) {
            Video.router.navigate(previousVideoFragment, {trigger: true});
            event.stopPropagation();
            return false;
        });
        $("a.next-video").click(function(event) {
            Video.router.navigate(nextVideoFragment, {trigger: true});
            event.stopPropagation();
            return false;
        });

        if (videoData.next_video_topic) {
            // Don't autoplay to next video
            VideoControls.setAutoPlayCallback(null);
        } else {
            VideoControls.setAutoPlayCallback(function() {
                Video.router.navigate(nextVideoFragment, {trigger: true});
            });
        }

        VideoControls.initContinuousPlayLinks($("span.video-content"));

        // Preload adjacent videos after 15 seconds
        setTimeout(function() {
            Video.loadVideo(previousVideoTopic, videoData.previous_video.readable_id);
            Video.loadVideo(nextVideoTopic, videoData.next_video.readable_id);
        }, 15000);

        this.waitingForVideo = null;
    },

    loadVideo: function(topic, video) {
        var fragment = video + "?topic=" + topic;
        if (videoLibrary[fragment]) {
            if (Video.waitingForVideo == fragment) {
                KAConsole.log("Switching to video: " + fragment);
                Video.renderPage(videoLibrary[fragment]);
            }
        } else {
            KAConsole.log("Loading video: " + fragment);
            url = "/api/v1/videos/" + topic + "/" + video + "/play";
            $.ajax({
                url: url,
                success: function(json) {
                    videoLibrary[fragment] = json;
                    if (Video.waitingForVideo == fragment) {
                        KAConsole.log("Switching to video: " + fragment);
                        Video.renderPage(json);
                    }
                }
            });
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
        ":video?topic=:topic": "video"
    },

    video: function(video, topic) {
        var fragment = video + "?topic=" + topic;
        Video.waitingForVideo = fragment;
        Video.loadVideo(topic, video);
    }
});

