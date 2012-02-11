
var Video = {

    SHOW_SUBTITLES_COOKIE: 'show_subtitles',

    init: function() {

        this.renderPage();

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

    renderPage: function() {
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

        // Set up next/previous links
        $("a.previous-video").click(function(event) {
            var url;
            if (videoData.previous_topic) {
                url = "/api/v1/videos/" + videoData.previous_video_topic.id + "/" + videoData.previous_video.readable_id + "/play";
            } else {
                url = "/api/v1/videos/" + videoData.topic.id + "/" + videoData.previous_video.readable_id + "/play";
            }
            $.ajax({
                url: url,
                success: function(json) {
                    window.videoData = json;
                    Video.renderPage();
                }
            });
            event.stopPropagation();
            return false;
        });
        $("a.next-video").click(function(event) {
            if (videoData.next_topic) {
                url = "/api/v1/videos/" + videoData.next_video_topic.id + "/" + videoData.next_video.readable_id + "/play";
            } else {
                url = "/api/v1/videos/" + videoData.topic.id + "/" + videoData.next_video.readable_id + "/play";
            }
            $.ajax({
                url: url,
                success: function(json) {
                    window.videoData = json;
                    Video.renderPage();
                }
            });
            event.stopPropagation();
            return false;
        });
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
}
