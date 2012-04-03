/**
 * A component to display a user hover card.

 Usage:
 <div class="video-footer">
    <span class="author-nickname">Katniss</span>
    <span class="author-nickname">Haymitch</span>
    <span class="author-nickname">Thresh</span>
 </div>

 $(".video-footer").on("mouseenter", ".author-nickname", function() {
     HoverCard.createHoverCardQtip($(this));
 });

 */

var HoverCard = {
    cache_: {},

    createHoverCardQtip: function(jel) {
        var userID = jel.data("user-id"),
            hasQtip = jel.data("has-qtip");

        if (!userID || hasQtip) {
            return;
        }

        var cachedHtml = HoverCard.cache_[userID],
            html;

        if (cachedHtml) {
            // We've hovered over the user somewhere else on the page
            html = cachedHtml;
        } else {
            // Create loading view
            var view = new HoverCardView(),
                html = view.render().el.innerHTML;

            $.ajax({
                type: "GET",
                url: "/api/v1/user/profile",
                data: {
                    casing: "camel",
                    userID: userID
                  },
                dataType: "json",
                success: _.bind(HoverCard.onHoverCardDataLoaded_, this, jel)
            });
        }

        jel.data("has-qtip", true);

        // Create tooltip
        jel.qtip({
                content: {
                    text: html
                },
                style: {
                    classes: "custom-override"
                },
                hide: {
                    delay: 100,
                    fixed: true
                },
                position: {
                    my: "top left",
                    at: "bottom left"
                }
            });

        jel.qtip("show");

    },

    onHoverCardDataLoaded_: function(jel, data) {
        var userID = jel.data("user-id"),
            model = new ProfileModel(data),
            view = new HoverCardView({model: model}),
            html = view.render().el.innerHTML;

        // Cache html for this user
        HoverCard.cache_[userID] = html;

        // Replace tooltip content
        jel.qtip("option", "content.text", html);
    }
}
