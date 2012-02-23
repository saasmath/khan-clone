
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

        $(".transcript-link").toggle(function(ev) {
            ev.preventDefault();
            $("#transcript").slideDown("fast", $.proxy(InteractiveTranscript.start, InteractiveTranscript));
        }, function(ev) {
            ev.preventDefault();
            InteractiveTranscript.stop();
            $("#transcript").slideUp("fast");
        });

        InteractiveTranscript.init();

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

// todo: when play is pushed on the video player, tick

var InteractiveTranscript = {
    // container for all subtitles
    subtitles: null,

    // currently highlighted subtitle
    currentSubtitle: null,

    // user clicked a subtitle, so override the video time with the subtitle time
    pendingSeek: null,

    // turn automatic scrolling on or off. Disabled when user manually uses the scrollbar
    autoScroll: true,

    // used to know if we've already scheduled a timeout due to visiblity
    visibleResume: false,

    // interval for resuming scrolling after a manual scroll
    resumeScrollIvl: null,

    // interval for triggering ticks
    tickIvl: null,

    // used for distinguishing between programmatic and user scroll events
    lastScrollTop: 0,

    init: function() {
        this.subtitles = $("#transcript");

        this.subtitles.find("a").bind("click", $.proxy(function( e ) {
            var player = VideoStats.player;

            // Stop from visiting the link
            e.preventDefault();

            // Grab the time to jump to from the subtitle
            this.pendingSeek = parseFloat( $(e.target).parent().data( "time" ) );

            // Jump to that portion of the video
            this.seek( player );

            // resume autoscrolling from this point
            this.autoScroll = true;
            clearInterval( this.resumeScrollIvl );
            this.resumeScrollIvl = null;

        }, this));

        // Get the subtitles and highlight the first one
        var lines = this.subtitles.find("li");
        this.currentSubtitle = lines.eq(0)
        this.currentSubtitle.addClass("active")[0];

        this.subtitles.scroll($.proxy(function(ev) {
            var currentScrollTop = ev.target.scrollTop;

            // scrollingProgrammatically is not completely reliable, so
            // only turn off autoscroll if we're scrolling by a large amount
            var tolerance = 3;
            var disableScroll = (!scrollingProgrammatically &&
                Math.abs(currentScrollTop - this.lastScrollTop) >= tolerance);

            if(disableScroll) {
                this.autoScroll = false;
                clearInterval( this.resumeScrollIvl );
                this.resumeScrollIvl = setTimeout($.proxy(function() {
                    this.autoScroll = true;
                }, this), 20000);
            }

            this.lastScrollTop = currentScrollTop;
        }, this));
    },

    start: function() {
        this.stop(); // for idempotency

        // Continually update the active subtitle position
        this.tick();
        this.tickIvl = setInterval($.proxy(this.tick, this), 333);
    },

    stop: function() {
        clearInterval(this.tickIvl);
        this.tickIvl = null;
    },

    tick: function() {
        var player = VideoStats.player;
        if(!player) return;

        var lines = this.subtitles.find("li");
        // Get the seek position or the current time
        // (allowing the user to see the transcript while loading)
        // We need to round the number to fix floating point issues
        var curTime = (this.pendingSeek || player.getCurrentTime()).toFixed(2);

        for ( var i = 0, l = lines.length; i < l; i++ ) {
            var lineTime = $(lines[i]).data("time");

            // We're looking for the next highest element before backtracking
            if ( lineTime > curTime && lineTime !== curTime ) {
                var nextSubtitle = lines[ i - 1 ];

                if ( nextSubtitle ) {
                    this.subtitleJump( nextSubtitle );
                    return;
                }
            }
        }

        // We've reached the end so make the last one active
        this.subtitleJump( lines[ i - 1 ] );
    },

    // Jump to a specific subtitle (either via click or automatically)
    subtitleJump: function( nextSubtitle ) {
        if ( nextSubtitle == this.currentSubtitle ) {
            return;
        }
        $(this.currentSubtitle).removeClass("active");
        $(nextSubtitle).addClass("active");
        this.currentSubtitle = nextSubtitle;

        if ( !this.autoScroll ) {
            // Resume scrolling if the subtitle view is positioned over the active subtitle
            var subtitleTop = this.currentSubtitle.offsetTop;
            var visibleTop = this.subtitles.scrollTop()
            var visibleBottom = visibleTop + this.subtitles[0].offsetHeight;
            var subtitleVisible =   subtitleTop >= visibleTop &&
                                    subtitleTop <= visibleBottom;

            if ( subtitleVisible ) {
                // resume autoscrolling in 5 s
                if (!this.visibleResume) {
                    this.visibleResume = true;
                    setTimeout($.proxy(function() {
                        this.autoScroll = true;
                        this.visibleResume = false;
                    }, this), 5000);
                }
            }
        }

        if ( this.autoScroll ) {
            // Adjust the viewport to animate to the new position
            var pos = this.desiredPos($("#transcript"), this.currentSubtitle);
            this.subtitles.scrollTo( pos );
        }
    },

    desiredPos: function(container, el) {
        // position of element relative to top of container
        // requires that container is the element's offsetParent
        var top = el.offsetTop;

        // need to scroll such that the element in placed in the center of the container
        var containerHeight = container.height();
        var elHeight = $(el).height();
        var aboveEl = (containerHeight - elHeight) / 2;
        var pos = Math.max( top - aboveEl, 0 );

        // Make sure that we don't end with whitespace at the bottom
        pos = Math.min( container[0].scrollHeight - containerHeight, pos );

        return pos;
    },

    // Seek to a specific part of a video
    seek: function( video ) {
        if ( this.pendingSeek !== null ) {
            video.seekTo(this.pendingSeek, true);
            this.pendingSeek = null;
        }
    }
};

var scrollingProgrammatically = true;
jQuery.fn.scrollTo = function( pos ) {
    if ( top == null ) {
        return this;
    }

    // Adjust the viewport to animate to the new position
    if ( jQuery.support.touch && this.hasClass("ui-scrollview-clip") ) {
        this.scrollview( "scrollTo", 0, pos, 200 );

    } else {
        scrollingProgrammatically = true;
        this.stop().animate( { scrollTop: pos }, {
            duration: 200,
            complete: function() {
                // We seem to get one "scroll" event after complete is called
                // Use a timeout in hopes that this gets run after that happens
                setTimeout( function() {
                    scrollingProgrammatically = false;
                }, 1 );
            }
        } );
    }

    return this;
};
