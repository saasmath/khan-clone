var Homepage = {

    init: function() {
        VideoControls.initThumbnails();
        Homepage.initWaypoints();
    },

    initPlaceholder: function(youtube_id) {

        var jelPlaceholder = $("#main-video-placeholder");

        // Once the youtube player is all loaded and ready, clicking the play
        // button will play inline.
        $(VideoControls).one("playerready", function() {

            // Before any playing, unveil and play the real youtube player
            $(VideoControls).one("beforeplay", function() {

                $(".player-loading-wrapper").removeClass("player-loading-wrapper");

                // This strange method of hiding the placeholder skips use of
                // display:none or position:absolute so Mozilla doesn't
                // re-layout and load its already-initialized <embed> video,
                // which causes a slight hiccup on click.
                jelPlaceholder.css("visibility", "hidden").height(0);

            });

            jelPlaceholder.click(function(e) {

                VideoControls.play();
                e.preventDefault();

            });

        });

        // Start loading the youtube player, and insert it wrapped
        // in a hidden container
        var template = Templates.get("homepage.youtube-embed");

        jelPlaceholder
            .parents("#main-video-link")
                .after(
                    $(template({"width": 480, "height": 395, "youtube_id": youtube_id}))
                        .wrap("<div class='player-loading-wrapper'/>")
                        .parent()
            );
    },

    initWaypoints: function() {

        // Waypoint behavior not supported in IE7-
        if ($.browser.msie && parseInt($.browser.version) < 8) return;

        $.waypoints.settings.scrollThrottle = 50;

        $("#browse").waypoint(function(event, direction) {

            var jel = $(this);
            var jelFixed = $("#browse-fixed")
            var jelTop = $("#back-to-top");

            jelTop.click(function(){Homepage.waypointTop(jel, jelFixed, jelTop);});

            if (direction == "down")
                Homepage.waypointVideos(jel, jelFixed, jelTop);
            else
                Homepage.waypointTop(jel, jelFixed, jelTop);
        });
    },

    waypointTop: function(jel, jelFixed, jelTop) {
        jelFixed.css("display", "none");
        if (!$.browser.msie) jelTop.css("display", "none");
    },

    waypointVideos: function(jel, jelFixed, jelTop) {
        jelFixed.css("width", jel.width()).css("display", "block");
        if (!$.browser.msie) jelTop.css("display", "block");
        if (CSSMenus.active_menu) CSSMenus.active_menu.removeClass('css-menu-js-hover');
    }
}

$(function(){Homepage.init();});
