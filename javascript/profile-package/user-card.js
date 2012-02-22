/**
 * Code to handle the public components of a profile.
 */

/**
 * Profile information about a user.
 * May be complete, partially filled, or mostly empty depending on the
 * permissions the current user has to this profile.
 */
var ProfileModel = Backbone.Model.extend({
    defaults: {
        "avatarName": "darth",
        "avatarSrc": "/images/darth.png",
        "countExercisesProficient": 0,
        "countVideosCompleted": 0,
        "dateJoined": "",
        "email": "",
        "isCoachingLoggedInUser": false,
        "nickname": "",
        "points": 0,
        "username": "",
        "isDataCollectible": false,
        "isSelf": false,
        "isPublic": false
    },

    url: "/api/v1/user/profile",

    isPhantom: function() {
        var email = this.get("email");
        return email.indexOf(ProfileModel.PHANTOM_EMAIL_PREFIX) === 0;
    },

    /**
     * Whether or not the current actor can customize this profile.
     * Note that users under 13 without parental consent can only
     * edit some data; clients should also check isDataCollectible for full
     * information about fields which can be edited.
     */
    isEditable: function() {
        return this.get("isSelf") && !this.isPhantom();
    },

    toJSON: function() {
        var json = ProfileModel.__super__.toJSON.call(this);
        json["isPhantom"] = this.isPhantom();
        json["isEditable"] = this.isEditable();

        // Ugh - handlebars can't do boolean logic in conditionals so we have
        // to do it here.
        json["isFullyEditable"] =
                this.isEditable() && this.get("isDataCollectible");
        return json;
    },

    /**
     * Returns the property from the JSON object if it exists.
     * Defaults to the current value of the property on "this".
     */
    getIfUndefined: function(obj, prop) {
        if (obj && obj[prop] !== undefined) {
            return obj[prop];
        }
        return this.get(prop);
    },

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
            "avatarName": this.getIfUndefined(attrs, "avatarName"),
            "nickname": $.trim(this.getIfUndefined(attrs, "nickname")),
            "username": this.getIfUndefined(attrs, "username"),
            "isPublic": this.getIfUndefined(attrs, "isPublic")
        });

        // Trigger a custom "savesuccess" event, since it's useful for clients
        // to know when certain operations succeeded on the server.
        var success = options.success;
        options.success = function(model, resp) {
            model.trigger("savesuccess");
            if (success) {
                success(model, resp);
            }
        };
        Backbone.Model.prototype.save.call(this, attrs, options);
    },

    // TODO: figure out how to do this in a more systematic way!
    // Override base Backbone.parse since badge modifications can result in
    // api_action_results to be sent back.
    parse: function(resp, xhr) {
        if ("apiActionResults" in resp && "payload" in resp) {
            resp = resp["payload"];
        }
        Backbone.Model.prototype.parse.call(this, resp, xhr);
    },

    /**
     * Toggle isCoachingLoggedInUser field client-side.
     * Update server-side if optional options parameter is provided.
     */
    toggleIsCoachingLoggedInUser: function(options) {
        var isCoaching = this.get("isCoachingLoggedInUser");

        this.set({"isCoachingLoggedInUser": !isCoaching});

        if (options) {
            options = $.extend({
                url: "/api/v1/user/coaches",
                type: isCoaching ? "DELETE" : "PUT",
                dataType: "json",
                contentType: "application/json",
                data: JSON.stringify({
                        coach: this.get("username") || this.get("email")
                    })
            }, options);

            $.ajax(options);
        }
    },

    validateNickname: function(nickname) {
        this.trigger("validate:nickname", ($.trim(nickname).length > 0));
    },

    validateUsername: function(username) {
        // Can't define validate() (or I don't understand how to)
        // because of https://github.com/documentcloud/backbone/issues/233

        // Remove any feedback if user returns to her current username
        if (username === this.get("username")) {
            this.trigger("validate:username");
            return;
        }

        // Must be consistent with canonicalizing logic on server.
        username = username.toLowerCase().replace(/\./g, "");

        // Must be synced with server's understanding
        // in UniqueUsername.is_valid_username()
        if (/^[a-z][a-z0-9]{2,}$/.test(username)) {
            $.ajax({
                url: "/api/v1/user/username_available",
                type: "GET",
                data: {
                    username: username
                },
                dataType: "json",
                success: _.bind(this.onValidateUsernameResponse_, this)
            });
        } else {
            var message = "";
            if (username.length < 3) {
                message = "Too short.";
            } else if (/^[^a-z]/.test(username)) {
                message = "Start with a letter.";
            } else {
                message = "Alphanumeric only.";
            }
            this.trigger("validate:username", message, false);
        }
    },

    onValidateUsernameResponse_: function(isUsernameAvailable) {
        var message = isUsernameAvailable ? "Looks good!" : "Not available.";
        this.trigger("validate:username", message, isUsernameAvailable);
    }
});

ProfileModel.PHANTOM_EMAIL_PREFIX = "http://nouserid.khanacademy.org/";

UserCardView = Backbone.View.extend({
    className: "user-card",

    events: {
        "click .add-remove-coach": "onAddRemoveCoachClicked_"
     },

     editEvents: {
         "click .avatar-pic-container": "onAvatarClick_",
         "mouseenter .avatar-pic-container": "onAvatarHover_",
         "mouseleave .avatar-pic-container": "onAvatarLeave_",
         "click #edit-profile": "onEditProfileClicked_",
         "click .sub_menu #edit-basic-info": "onEditBasicInfoClicked_",
         "click .sub_menu #edit-display-case": "onEditDisplayCaseClicked_",
         "click .sub_menu #edit-avatar": "onAvatarClick_",
         "click .sub_menu #edit-visibility": "onEditVisibilityClicked_",
         "click .edit-visibility": "onEditVisibilityClicked_"
     },

    initialize: function() {
        this.template = Templates.get("profile.user-card");

        this.model.bind("change:avatarSrc", _.bind(this.onAvatarChanged_, this));
        this.model.bind("change:isCoachingLoggedInUser",
                _.bind(this.onIsCoachingLoggedInUserChanged_, this));
        this.model.bind("change:nickname", function(model) {
                $(".nickname").text(model.get("nickname"));
        });
        this.model.bind("change:isPublic", this.onIsPublicChanged_);

        /**
         * The picker UI component which shows a dialog to change the avatar.
         * @type {Avatar.Picker}
         */
        this.avatarPicker_ = null;
        this.usernamePicker_ = null;
    },

    /**
     * Updates the source preview of the avatar. This does not affect the model.
     */
    onAvatarChanged_: function() {
        this.$("#avatar-pic").attr("src", this.model.get("avatarSrc"));
    },

    render: function() {
        var json = this.model.toJSON();
        // TODO: this data isn't specific to any profile and is more about the library.
        // It should probably be moved out eventially.
        json["countExercises"] = UserCardView.countExercises;
        json["countVideos"] = UserCardView.countVideos;
        $(this.el).html(this.template(json)).find("abbr.timeago").timeago();

        this.delegateEditEvents_();

        return this;
    },

    delegateEditEvents_: function() {
        if (this.model.isEditable()) {
            this.bindQtip_();
            this.delegateEvents(this.editEvents);
        }
    },

    bindQtip_: function() {
        this.$("#edit-visibility").qtip({
            content: {
                text: "Making your profile public will make the information in this user card visible to anyone who visits your profile page. It will also allow your user card to show up when your friends search for you.",
                title: {
                    text: "Profile Privacy Setting"
                }
            },
            style: {
                classes: "ui-tooltip-light ui-tooltip-shadow",
                width: "250px"
            },
            position: {
                my: "top right",
                at: "bottom center"
            },
            show: {
                delay: 500
            },
            hide: {
                fixed: true,
                delay: 150
            }
        });
    },

    onAvatarHover_: function(e) {
        this.$(".avatar-change-overlay").show();
    },

    onAvatarLeave_: function(e) {
        this.$(".avatar-change-overlay").hide();
    },

    onAvatarClick_: function(e) {
        if (!this.avatarPicker_) {
            this.avatarPicker_ = new Avatar.Picker(this.model);
        }
        this.avatarPicker_.show();
    },

    onAddRemoveCoachClicked_: function(e) {
        var options = {
            success: _.bind(this.onAddRemoveCoachSuccess_, this),
            error: _.bind(this.onAddRemoveCoachError_, this)
        };

        this.model.toggleIsCoachingLoggedInUser(options);
    },

    onAddRemoveCoachSuccess_: function(data) {
        // TODO: message to user
    },

    onAddRemoveCoachError_: function(data) {
        // TODO: message to user

        // Because the add/remove action failed,
        // toggle back to original client-side state.
        this.model.toggleIsCoachingLoggedInUser();
    },

    /**
     * Toggles the display of the add/remove coach buttons.
     * Note that only one is showing at any time.
     */
    onIsCoachingLoggedInUserChanged_: function() {
        this.$(".add-remove-coach").toggle();
    },

    /**
     * On a click outside the edit profile submenu,
     * hide the submenu and unbind this handler.
     */
    getBoundHideSubMenuFn_: function() {
        if (!this.boundHideSubMenuFn_) {
            this.boundHideSubMenuFn_ = _.bind(function(e) {
                var jelSubMenu = $(".sub_menu");
                for (var node = e.target; node; node = node.parentNode) {
                    if (node === jelSubMenu.get(0)) {
                        // Click inside the submenu somewhere - ignore.
                        return;
                    }
                }
                jelSubMenu.hide();
                $(document).unbind(e);
            }, this);
        }
        return this.boundHideSubMenuFn_;
    },

    onEditProfileClicked_: function(evt) {
        evt.stopPropagation();
        var jelSubMenu = $(".sub_menu").toggle();

        if (jelSubMenu.is(":visible")) {
            $(document).bind("mousedown", this.getBoundHideSubMenuFn_());
        } else {
            // Because the edit profile button can also hide the submenu,
            // unbind this handler so they don't pile up.
            $(document).unbind("mousedown", this.getBoundHideSubMenuFn_());
        }
    },

    onEditBasicInfoClicked_: function(evt, setPublic) {
        if (!this.usernamePicker_) {
            this.usernamePicker_ = new UsernamePickerView({model: this.model});
            $("body").append(this.usernamePicker_.render().el);
        }
        this.usernamePicker_.toggle(setPublic);
    },

    onEditDisplayCaseClicked_: function(e) {
        // TODO: Consider handling outside-the-widget dismissal clicks differently
        e.stopPropagation();
        $(".display-case-cover").click();
    },

    onEditVisibilityClicked_: function(e) {
        if (!this.model.get("username")) {
            // Profiles can't be made public until the user acquires a
            // username first. Pop up the dialog to do that.
            this.onEditBasicInfoClicked_(null, true);
            return;
        }
        var isPublic = this.model.get("isPublic");
        this.model.save({ isPublic: !isPublic });
    },

    onIsPublicChanged_: function(model, isPublic) {
        var jel = $(".visibility-toggler");
        if (isPublic) {
            jel.removeClass("private")
                .addClass("public")
                .text("Profile is public");
        } else {
            jel.removeClass("public")
                .addClass("private")
                .text("Profile is private");
        }
        jel.effect("bounce");
    }

});

// TODO: these should probably go into some other place about the library.
/**
 * The total number of videos in the Khan Academy library.
 */
UserCardView.countVideos = 0;

/**
 * The total number of exercises in the Khan Academy library.
 */
UserCardView.countExercises = 0;

