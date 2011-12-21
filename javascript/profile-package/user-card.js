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

        "avatarName": "darth",
        "avatarSrc": "/images/darth.png"
    },

    url: "/api/v1/user/profile",

    /**
     * Override Backbone.Model.save since only some of the fields are
     * mutable and saveable.
     */
    save: function(attrs, options) {
        options = options || {};
        options.contentType = "application/json";
        options.data = JSON.stringify({
            // Note that Backbone.Model.save accepts arguments to save to
            // the model before saving, so check for those first.
            "avatarName": ( attrs && attrs[ "avatarName" ]) ||
                          this.get( "avatarName" ),
            "nickname": ( attrs && attrs[ "nickname" ]) ||
                          this.get( "nickname" )
        });
        Backbone.Model.prototype.save.call(this, attrs, options);
    }
});

UserCardView = Backbone.View.extend({
    className: "user-info",

    events: {
        "click .avatar-pic-container": "onAvatarClick_",
        "mouseenter .avatar-pic-container": "onAvatarHover_",
        "mouseleave .avatar-pic-container": "onAvatarLeave_",
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

    /**
     * Updates the source preview of the avatar. This does not affect the model.
     */
    onAvatarChanged_: function() {
        this.$("#avatar-pic").attr( "src", this.model.get( "avatarSrc" ));
    },

    render: function() {
        $( this.el ).html( this.template( this.model.toJSON() ) )
            .find( "abbr.timeago" ).timeago();
        return this;
    },

    /**
     * Handles a change to the nickname edit field in the view.
     * Propagates the change to the model.
     */
    onNicknameChanged_: function( e ) {
        // TODO: validate
        var value = this.$("#nickname").val();
        this.model.save({ "nickname": value });
    },

    onAvatarHover_: function( e ) {
        this.$(".avatar-change-overlay").show();
    },

    onAvatarLeave_: function( e ) {
        this.$(".avatar-change-overlay").hide();
    },

    onAvatarClick_: function( e ) {
        if ( !this.avatarPicker_ ) {
            this.avatarPicker_ = new Avatar.Picker( this.model );
        }
        this.avatarPicker_.show();
    }

});
