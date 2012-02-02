/**
 * Code to handle the profile info changer.
 * TODO: rename away from username picker
 */

UsernamePickerView = Backbone.View.extend({
    id: "username-picker-container",
    setPublicAfterSave_: false,

    events: {
        "keyup .nickname": "onNicknameKeyup_",
        "keyup .username": "onUsernameKeyup_",
        "click #save-profile-info": "onSaveClick_",
        "click #cancel-profile-info": "toggle"
    },

    initialize: function() {
        this.template = Templates.get("profile.username-picker");
        this.shouldShowUsernameWarning_ = false;
        this.keyupTimeout = null;
        this.model.bind("validate:nickname",
            _.bind(this.onValidateNickname_, this));
        this.model.bind("validate:username",
            _.bind(this.onValidateUsername_, this));
    },

    render: function() {
        // TODO: Make idempotent
        // maybe making the resetFields_ function obsolete
        var context = {
                username: this.model.get("username"),
                nickname: this.model.get("nickname")
            },
            html = this.template(context);

        $(this.el).html(html)
            .addClass("modal fade hide")
            .modal({
                keyboard: true,
                backdrop: true
            })
            .bind("hidden", _.bind(this.resetFields_, this))
            .bind("shown", _.bind(this.onPickerShown_, this));
        return this;
    },

    toggle: function(setPublic) {
        $(this.el).modal("toggle");
        this.setPublicAfterSave_ = setPublic;
        if (setPublic) {
            $(".notification.info").show();
            $("#save-profile-info").val("Save and make profile public");
        }
    },

    resetFields_: function() {
        var nickname = this.model.get("nickname"),
            username = this.model.get("username");

        this.$(".notification").hide();
        this.$(".nickname").val(nickname);
        this.$(".username").val(username);
        this.$(".example-username").val(username);
        this.$(".sidenote").text("").removeClass("success").removeClass("error");
        this.$("#save-profile-info").prop("disabled", false).val("Save");
    },

    onPickerShown_: function() {
        // If the user already has a username, be sure that we warn them about
        // the holding period that happens if they change it.
        Promos.hasUserSeen("Username change warning", function(hasSeen) {
            this.shouldShowUsernameWarning_ = !hasSeen;
        }, this);
    },

    onNicknameKeyup_: function() {
        this.model.validateNickname(this.$(".nickname").val());
    },

    onUsernameKeyup_: function(e) {
        if (this.shouldShowUsernameWarning_ && this.model.get("username")) {
            $(".notification.error").show();
            Promos.markAsSeen("Username change warning");
            this.shouldShowUsernameWarning_ = false;
        }
        if (e.keyCode === 13) {
            // Pressing enter does not save. Should it?
            this.onTimeout_();
            return;
        }
        this.$(".example-username").text(this.$(".username").val());

        if (this.keyupTimeout) {
            clearTimeout(this.keyupTimeout);
        }
        this.keyupTimeout = setTimeout(_.bind(this.onTimeout_, this), 1000);
    },

    onTimeout_: function() {
        this.showSidenote_(".username-row", "Checking...");
        this.$("#save-profile-info").prop("disabled", true);
        this.model.validateUsername(this.$(".username").val());
        this.keyupTimeout = null;
    },

    onValidateNickname_: function(isValid) {
        if (isValid) {
            this.showSidenote_(".nickname-row", "");
        } else {
            this.showSidenote_(".nickname-row", "Too short.", false);
        }
    },

    onValidateUsername_: function(message, isValid) {
        this.showSidenote_(".username-row", message, isValid);
    },

    /**
     * Show the message in the specified row's sidenote.
     * If isValid === true, show a green checkmark (success),
     * if isValid === false, show a red x (error),
     * otherwise, don't show any such indicator.
     */
    showSidenote_: function(rowSelector, message, isValid) {
        var jelSidenote = this.$(rowSelector).find(".sidenote"),
            message = message || "";

        jelSidenote.removeClass("error").removeClass("success");

        if (isValid === true) {
            jelSidenote.addClass("success");
        } else if (isValid === false){
            jelSidenote.addClass("error");
        }

        this.$("#save-profile-info").prop("disabled", (isValid === false));

        jelSidenote.text(message);
    },

    onChangeSuccess_: function(model, response) {
        this.toggle();
    },

    onChangeError_: function(model, response) {
        this.onValidateUsername_(response.responseText, false);
    },

    onSaveClick_: function() {
        var nickname = this.$(".nickname").val(),
            username = this.$(".username").val(),
            attrs = {
                nickname: nickname,
                username: username
            },
            options = {
                success: _.bind(this.onChangeSuccess_, this),
                error: _.bind(this.onChangeError_, this)
            };

        this.model.save(attrs, options);

        if (this.setPublicAfterSave_) {
            $("#edit-visibility").click();
        }
    }
});
