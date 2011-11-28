var Homepage = {

    init: function() {
        VideoControls.initThumbnails();
        Homepage.initWaypoints();
		Homepage.loadData();
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
    },

    loadData: function() {
        $.ajax({
			type: "GET",
			url: "/api/v1/homepage_library",
			dataType: "jsonp",
            jsonpCallback: "__dataCb",
			success: function(data){
				Homepage.loadLibraryContent(data);
			},
			error: function() {
				console.log("error loading");
			},
            cache: true
        });
    },

    loadLibraryContent: function(content) {
        var playlists = [];
        function visitTopicOrPlaylist(item) {
            if (item["playlist"]) {
                // Playlist item - add to the master list.
                playlists.push(item["playlist"]);
                return;
            }
            // Otherwise it's a topic with sub-playlists or sub-topics
            var subItems = item["items"];
            if (subItems) {
                for (var i = 0, sub; sub = subItems[i]; i++) {
                    visitTopicOrPlaylist(sub);
                }
            }
        }
        for (var i = 0, item; item = content[i]; i++) {
            visitTopicOrPlaylist(item);
        }

        for (var i = 0, playlist; playlist = playlists[i]; i++) {
            var title = playlist["title"];
			var sluggified = playlist["slugged_title"];
            var videos = playlist["videos"]
            var videosPerCol = Math.ceil(videos.length / 3)
            var colHeight = videosPerCol * 18;
            var html = [];
            for (var j = 0, video; video = videos[j]; j++) {
                var col = (j / videosPerCol) | 0;
                var readableId = video["readable_id"];
                var videoKeyId = video["key_id"];
                var videoTitleEscaped = video["title"]; // TODO: escape

                html.push("<li class=\"m", col, "\"");
                if ((j % videosPerCol == 0) && col > 0) {
                    // First in the column
                    html.push(" style=\"margin-top:-", colHeight, "px;\"");
                }
                html.push(">");
                html.push("<a href=\"/video/", readableId,
                        "?playlist=", encodeURIComponent(title), "\" ",
                        "class=\"vl\">",
                        "<span class=\"vid-progress v", videoKeyId, "\">",
                        videoTitleEscaped,
                        "</span",
                        "</a></li>");
            }

            var container = $("#" + sluggified + " ol").get(0);
            container.style.height = colHeight + "px";
            container.innerHTML = html.join("");
		}
    }
}

$(function(){Homepage.init();});
