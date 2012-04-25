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
        return email && email.indexOf(ProfileModel.PHANTOM_EMAIL_PREFIX) === 0;
    },

    isInaccessible: function() {
        // TODO(marcia): Learn from BenKomalo on how to deal with this nicely
        // Maybe follow UserProfile?
        return (this.get("avatarName") === "darth");
    },

    /**
     * Whether or not the current actor on the app can access this user's full
     * profile information.
     */
    isFullyAccessible: function() {
        // Right now we're using "email" as a proxy for full information, since
        // the server will not send down the e-mail address if you don't have
        // the full information.
        return this.get("isSelf") || !!this.get("email");
    },

    /**
     * Returns either an e-mail or username that will uniquely identify the
     * user.
     *
     * Note that not all users have a username, and not all users have
     * an e-mail. However, if the actor has full access to this profile,
     * at least one of these values will be non empty.
     */
    getIdentifier: function() {
        return this.get("username") || this.get("email");
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
        json["isFullyAccessible"] = this.isFullyAccessible();
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
