
var Video = {

    SHOW_SUBTITLES_COOKIE: "show_subtitles",

    init: function() {

        VideoControls.onYouTubeBlocked(function() {
           $("#youtube_blocked").css("visibility", "visible").css("left", "0px").css("position", "relative");
           $("#idOVideo").hide();
           VideoStats.prepareAlternativePlayer(); // If YouTube is hidden, use the flv player for statistics
        });

        var jVideoDropdown = $("#video_dropdown");
        if (jVideoDropdown.length) {
            jVideoDropdown.css("display", "inline-block");

            var menu = $("#video_dropdown ol").menu();
            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css("position", "absolute");
            menu.bind("menuselect", function(e, ui) {
                window.location.href = ui.item.children("a").attr("href");
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

        $(".and-more").click(function() {
            $(this).hide();
            $(".more-content").show();
            return false;
        });

        $(".subtitles-link").click(function() { Video.toggleSubtitles(); return false; });
        if (readCookie(this.SHOW_SUBTITLES_COOKIE)) {
            this.showSubtitles();
        }

        var transcript = $(".subtitles-container");
        $(".transcript-link").toggle(function(ev) {
            transcript.slideDown("fast", function() {
                InteractiveTranscript.start();
            });
        }, function(ev) {
            InteractiveTranscript.stop();
            transcript.slideUp("fast");
        });

        InteractiveTranscript.init(transcript);

        $(".sharepop").hide();
        $(".share-link").click(function() {
            $(this).next(".sharepop").toggle("drop", {direction: "up"},"fast");
            return false;
        });
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
        $(".unisubs-videoTab").hide();
        $(".subtitles-warning").hide();
        $(".youtube-video").css("marginBottom", "0px");
        Throbber.hide();
    },

    showSubtitleElements: function() {
        $(".youtube-video").css("marginBottom", "32px");
        $(".subtitles-warning").show();
        $(".unisubs-videoTab").show();
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

/*
 * Widget for interactive video subtitles.
 *
 * The video transcript is displayed with the current subtitle "active".
 * Clicking a subtitle jumps to that place in the video. The transcript
 * viewport is scrolled to keep the current subtitle in view.
 */
var InteractiveTranscript = {

    /*
     * The frequency in milliseconds at which to check the visible subtitle.
     */
    POLL_MILLIS: 333,

    /*
     * The "active" subtitle.
     */
    activeSubtitle: null,

    /*
     * Whether automatic scrolling is enabled. Turned off when the user is
     * interacting with the transcript.
     */
    autoscroll: true,

    /*
     * The polling interval ID returned by window.setInterval().
     */
    pollInterval: null,

    /*
     * The scrollable area containing subtitles.
     */
    viewport: null,

    /*
     * Initialize with the interactive transcript root element. Call only once.
     */
    init: function(root) {
        //console.log("InteractiveTranscript.init()");
        var viewport = root.find(".subtitles");
        viewport.delegate("a", "click", $.proxy(this._onsubtitleclick, this));
        viewport.hover($.proxy(this._onhover, this));
        this.viewport = viewport;
    },

    /*
     * Begin tracking the active subtitle in the video player.
     */
    start: function() {
        //console.log("InteractiveTranscript.start()");
        this.stop();
        this._pollPlayer();
        this.pollInterval = setInterval(
            $.proxy(this._pollPlayer, this), this.POLL_MILLIS);
    },

    /*
     * Stop tracking the active subtitle in the video player.
     */
    stop: function() {
        //console.log("InteractiveTranscript.stop()");
        clearInterval(this.pollInterval);
        this.pollInterval = null;
    },

    /*
     * Handle mouseenter and mouseleave on the transcript.
     */
    _onhover: function(e) {
        //console.log("InteractiveTranscript._onhover(): type="+e.type);
        this.autoscroll = (e.type === "mouseleave");
    },

    /*
     * Handle click event on a subtitle.
     */
    _onsubtitleclick: function(e) {
        //console.log("InteractiveTranscript._onsubtitleclick()");
        if (!VideoStats.player) {
            return;
        }

        var time = parseFloat($(e.target).parent().data("time"));

        if (!isNaN(time)) {
            VideoStats.player.seekTo(time, true);
        }
    },

    /*
     * Activate the subtitle corresponding to the current video position.
     */
    _pollPlayer: function() {
        //console.log("InteractiveTranscript._pollPlayer()");
        if (!VideoStats.player) {
            return;
        }

        var currTime = VideoStats.player.getCurrentTime(),
            lineTime,
            currSub,
            lines = this.viewport.find("li"),
            len = lines.length,
            i;

        for (i = 0; i < len; i++) {
            lineTime = parseFloat($(lines[i]).data("time"));

            // find the next highest element before stepping back by 1
            if (!isNaN(lineTime) && lineTime > currTime) {
                currSub = (i === 0) ? lines[0] : lines[i - 1];
                break;
            }
        }

        if (currSub !== this.activeSubtitle) {
            this._setActiveSubtitle(currSub || lines[len - 1]);
        }
    },

    /*
     * Activate the given subtitle.
     */
    _setActiveSubtitle: function(subtitle) {
        //console.log("InteractiveTranscript._setActiveSubtitle()");

        var activeSubtitle = this.activeSubtitle,
            offsetTop,
            height;

        if (activeSubtitle) {
            $(activeSubtitle).removeClass("active");
        }
        $(subtitle).addClass("active");
        this.activeSubtitle = subtitle;

        if (this.autoscroll) {
            offsetTop = subtitle.offsetTop;
            height = $(subtitle).height();

            // show three lines above the active line
            this.viewport.stop().animate({
                scrollTop: offsetTop - (height * 3)
            });
        }
    }
};

