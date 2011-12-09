/**
 * Code to handle the public components of a profile.
 */

// UserCardModel's fields mostly come from util_profile.py
// and so they do not match UserData
UserCardModel = Backbone.Model.extend({
    defaults: {
        "loggedIn": false,
        "points": 0,
        "countVideosCompleted": 0,
        "countVideos": 3000,
        "countExercisesProficient": 0,
        "countExercises": 250
    }
});

UserCardView = Backbone.View.extend({
    className: "user-info",

    initialize: function() {
        this.template = Templates.get( "profile.user-card" );
    },

    render: function() {
        $( this.el ).html( this.template( this.model.toJSON() ) )
            .find( "abbr.timeago" ).timeago();
        return this;
    }
});
