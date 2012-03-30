(function() {
    // The video data for the subtopics of this topic
    var videosByTopic = {};

    // The currently selected subtopic in the content pane
    var selectedTopic = null;
    
    window.TopicPage = {
        init: function(videoLists, marqueeVideoID) {
            var selectedID = videoLists[0].id;
            var self = this;

            _.each(videoLists, function(topic) {
                videosByTopic[topic.id] = topic;
            });

            $(".topic-page-content .nav-pane li.selected").each(function(idx, selected) {
                selectedID = $(selected).attr("data-id");
            });

            selectedTopic = videosByTopic[selectedID];

            selectedTopic.view = selectedTopic.view || new this.ContentTopicView({ model: selectedTopic });
            selectedTopic.view.show();

            $(".topic-page-content .nav-pane").on("click", "a", function() {
                selectedID = $(this).attr("data-id");
                selectedTopic = videosByTopic[selectedID];

                selectedTopic.view = selectedTopic.view || new self.ContentTopicView({ model: selectedTopic });
                selectedTopic.view.show();

                $(".topic-page-content .nav-pane li.selected").removeClass("selected");
                $(this).parent().addClass("selected");
            });

            VideoControls.initPlaceholder($(".main-video-placeholder"), { "youtubeId": marqueeVideoID });

            $(window).resize(function() {self.resize();});
            this.resize();
        },

        resize: function() {
            var jelContent = $(".topic-page-content");
            var containerHeight = $(window).height();
            var yTopPadding = jelContent.offset().top;
            var yBottomPadding = $("#end-of-page-spacer").outerHeight(true);
            var newHeight = containerHeight - (yTopPadding + yBottomPadding * 2 + 6);

            jelContent.height(newHeight);
        },

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
