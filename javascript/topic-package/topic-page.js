(function() {
    // The video data for the subtopics of this topic
    var videosByTopic = {};

    // The currently selected subtopic in the content pane
    var selectedTopic = null;

    // The topic information for the current page's topic
    var rootPageTopic = null;

    // View for the root topic in the content pane
    var rootTopicView = null;
    
    window.TopicPage = {
        init: function(videoLists, rootPath, rootTopic) {
            var selectedID = videoLists[0].id;
            var self = this;

            rootPageTopic = rootTopic;

            // TODO(tomyedwab): Temporary, should move this to a shared lib 
            Handlebars.registerPartial("youtube-player", Templates.get("shared.youtube-player"));

            _.each(videoLists, function(topic) {
                videosByTopic[topic.id] = topic;
            });

            $(".topic-page-content .nav-pane").on("click", "a", function() {
                selectedID = $(this).attr("data-id");
                self.router.navigate("/" + selectedID, true);
                return false;
            });

            VideoControls.initThumbnailHover();
            $("#thumbnails").find(".thumbnail_link").click(function(ev) {
                var video = {
                    youtube_id: $(this).parent().attr("data-youtube-id")
                };
                ModalVideo.show(video);
                ev.preventDefault();
                return false;
            });

            this.router = new this.SubTopicRouter();
            this.router.bind("all", Analytics.handleRouterNavigation);
            Backbone.history.start({pushState: true, root: rootPath});
        },

        SubTopicRouter: Backbone.Router.extend({
            routes: {
                "*subtopicID": "subtopic"
            },

            subtopic: function(subtopicID) {
                var selectedTopicID = '';
                if (subtopicID.charAt(0) == '/') {
                    subtopicID = subtopicID.substr(1);
                }

                KAConsole.log("Switching to subtopic: " + subtopicID);
                if (subtopicID == "") {
                    selectedTopic = null;
                } else {
                    selectedTopic = videosByTopic[subtopicID] || null;
                }

                if (selectedTopic) {
                    selectedTopic.view = selectedTopic.view || new TopicPage.ContentTopicView({ model: selectedTopic });
                    selectedTopic.view.show();
                    selectedTopicID = selectedTopic.id;
                } else {
                    rootTopicView = rootTopicView || new TopicPage.RootTopicView({ model: rootPageTopic });
                    rootTopicView.show();
                }

                $(".topic-page-content .nav-pane")
                    .find("li.selected")
                        .removeClass("selected")
                        .end()
                    .find("li[data-id=\"" + selectedTopicID + "\"]")
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
        }),

        RootTopicView: Backbone.View.extend({
            template: Templates.get("topic.root-topic-view"),
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
