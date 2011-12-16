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
        "countExercises": 250,
        "avatarSrc": "/images/darth.png"
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
        "click #avatar-pic": "onAvatarClick_",
        "change #nickname": "onNicknameChanged_"
    },

    initialize: function() {
        this.template = Templates.get( "profile.user-card" );
        this.model.bind( "change:avatarSrc", _.bind( this.onAvatarChanged_, this ));

        /**
         * The picker UI component which shows a dialog to change the avatar.
         * @type {Avatar.Picker}
         */
        this.avatarPicker_ = null;
    },

    onAvatarChanged_: function() {
        this.$("#avatar-pic").attr( "src", this.model.get( "avatarSrc" ));
    },

    render: function() {
        $( this.el ).html( this.template( this.model.toJSON() ) )
            .find( "abbr.timeago" ).timeago();
        return this;
    },

    onNicknameChanged_: function( e ) {
        // TODO: validate
        var value = this.$("#nickname").val();
        this.model.set({ "nickname": value });
        this.model.save();
    },

    onAvatarClick_: function( e ) {
        if ( !this.avatarPicker_ ) {
            this.avatarPicker_ = new Avatar.Picker( this.model );
        }
        this.avatarPicker_.show();
    }

});
