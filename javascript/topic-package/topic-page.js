(function() {
    // The video data for the subtopics of this topic
    var videosByTopic = {};

    // The currently selected subtopic in the content pane
    var selectedTopic = null;

    // The topic we fall back to if there's no subtopic selected
    var defaultTopic = null;
    
    window.TopicPage = {
        init: function(videoLists, marqueeVideoID, rootPath) {
            var selectedID = videoLists[0].id;
            var self = this;

            _.each(videoLists, function(topic) {
                videosByTopic[topic.id] = topic;
            });

            defaultTopic = videoLists[0];

            $(".topic-page-content .nav-pane").on("click", "a", function() {
                selectedID = $(this).attr("data-id");
                self.router.navigate("/" + selectedID, true);
                return false;
            });

            VideoControls.initPlaceholder($(".main-video-placeholder"), { "youtubeId": marqueeVideoID });

            $(window).resize(function() {self.resize();});
            this.resize();

            this.router = new this.SubTopicRouter();
            this.router.bind("all", Analytics.handleRouterNavigation);
            Backbone.history.start({pushState: true, root: rootPath});
        },

        resize: function() {
            var jelContent = $(".topic-page-content");
            var containerHeight = $(window).height();
            var yTopPadding = jelContent.offset().top;
            var yBottomPadding = $("#end-of-page-spacer").outerHeight(true);
            var newHeight = containerHeight - (yTopPadding + yBottomPadding * 2 + 6);

            jelContent.height(newHeight);
        },

        SubTopicRouter: Backbone.Router.extend({
            routes: {
                "*subtopicID": "subtopic"
            },

            subtopic: function(subtopicID) {
                if (subtopicID.charAt(0) == '/') {
                    subtopicID = subtopicID.substr(1);
                }

                KAConsole.log("Switching to subtopic: " + subtopicID);
                if (subtopicID == "") {
                    selectedTopic = defaultTopic;
                } else {
                    selectedTopic = videosByTopic[subtopicID];
                    if (!selectedTopic) {
                        selectedTopic = defaultTopic;
                    }
                }

                selectedTopic.view = selectedTopic.view || new TopicPage.ContentTopicView({ model: selectedTopic });
                selectedTopic.view.show();

                $(".topic-page-content .nav-pane")
                    .find("li.selected")
                        .removeClass("selected")
                        .end()
                    .find("li[data-id=\"" + selectedTopic.id + "\"]")
                        .addClass("selected");
            }
        }),

        ContentTopicView: Backbone.View.extend({
            template: Templates.get("topic.content-topic-videos"),
            initialize: function() {
                this.render();
            },

            render: function() {
                $(this.el).html(this.template(this.model));
            },

            show: function() {
                $(".topic-page-content .content-pane .content-inner")
                    .children()
                        .detach()
                        .end()
                    .append(this.el);
            }
        })
    };
})();
