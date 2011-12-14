/**
 * Code to handle the public components of a profile.
 */

// UserCardModel's fields mostly come from util_profile.py
// and so they do not match UserData
UserCardModel = Backbone.Model.extend({
    defaults: {
        "loggedIn": false,
        "nickname": "",
        "dateJoined": "",
        "points": 0,
        "countVideosCompleted": 0,
        "countVideos": 3000,
        "countExercisesProficient": 0,
        "countExercises": 250
    },

    url: "/api/v1/user/profile",

    /**
     * Override Backbone.Model.Save since only some of the fields are
     * mutable and saveable.
     */
    save: function(attrs, options) {
        options = options || {};
        options.contentType = "application/json";
        options.data = JSON.stringify({
            "nickname": this.get( "nickname" )
        });
        Backbone.Model.prototype.save.call(this, attrs, options);
    }
});

UserCardView = Backbone.View.extend({
    className: "user-info",

    events: {
        "change #nickname": "onNicknameChanged_"
    },

    initialize: function() {
        this.template = Templates.get( "profile.user-card" );
    },

    render: function() {
        $( this.el ).html( this.template( this.model.toJSON() ) )
            .find( "abbr.timeago" ).timeago();
        return this;
    },

    onNicknameChanged_: function( e ) {
        // TODO: validate
        var value = this.$("#nickname").val()
        this.model.set({ "nickname": value });
        this.model.save();
    }
});
