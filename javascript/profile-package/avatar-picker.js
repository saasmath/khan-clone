/**
 * A component to display a list of avatars and select one for
 * the current user.
 *
 * Avatars are pre-defined from a list that a user has access to.
 * The mechanics of which avatars are accessable are externalized
 * and not specific to this implementation.
 */

/** Namespace. */
var Avatar = Avatar || {};


/**
 * The main UI component which displays a modal dialog to select
 * a list of avatars for an image.
 * @constructor
 */
Avatar.Picker = function(userModel) {
    /**
     * The container element of the dialog.
     */
    this.el = null;

    /**
     * The root element of the dialog contents.
     */
    this.contentEl = null;

    /**
     * The underlying model for the user profile that gets modified
     * when an avatar is selected.
     */
    this.userModel = userModel;
};

Avatar.Picker.template = Templates.get( "profile.avatar-picker" );

/**
 * Renders the contents of the picker and displays it.
 */
Avatar.Picker.prototype.getTemplateContext_ = function() {
    // Dummy data for now. Replace with the real thing.
    return {
        selectedSrc: this.userModel.get( "avatarSrc" ),
        categories: [
            {
                title: "Easy avatars",
                avatars: [
                    {
                        name: "Easy 1",
                        imageSrc: "http://www.trinigamers.com/forums/images/avatars/warp_ray_128.gif"
                    }, {
                        name: "Easy 2",
                        imageSrc: "http://www.trinigamers.com/forums/images/avatars/raynor1_128.gif"
                    }
                ]
            }, {
                title: "Medium avatars",
                avatars: [
                    {
                        name: "Medium 1",
                        imageSrc: "http://www.trinigamers.com/forums/images/avatars/findlay1_128.gif"
                    }, {
                        name: "Medium 2",
                        imageSrc: "http://www.trinigamers.com/forums/images/avatars/selendis_128.gif"
                    }
                ]
            }, {
                title: "Hard avatars",
                avatars: [
                    {
                        name: "Hard 1",
                        imageSrc: "http://www.trinigamers.com/forums/images/avatars/zergling_128.gif"
                    }
                ]
            }
        ]
    };
};

/**
 * Binds event handlers necessary to make this interactive.
 */
Avatar.Picker.prototype.bindEvents_ = function() {
    $(this.el).delegate(
            ".category-avatars .avatar",
            "click",
            _.bind( this.onAvatarSelected_, this ));

    $(this.el).delegate(
            ".category-avatars .avatar",
            "mouseenter",
            function( ev ) {
                $(ev.currentTarget).addClass("hover");
            });
    $(this.el).delegate(
            ".category-avatars .avatar",
            "mouseleave",
            function( ev ) {
                $(ev.currentTarget).removeClass("hover");
            });

    this.userModel.bind( "change:avatarSrc",
            _.bind( this.onAvatarChanged_, this ));
};

/**
 * Handles a selection to an avatar in the list.
 */
Avatar.Picker.prototype.onAvatarSelected_ = function( ev ) {
    var src = $("img.avatar-preview", ev.currentTarget).attr( "src" );
    if ( src ) {
        this.userModel.set({ "avatarSrc": src });
    }
};

/**
 * Handles a change to the selected avatar.
 */
Avatar.Picker.prototype.onAvatarChanged_ = function() {
    $("#selected-img", this.contentEl).attr(
           "src", this.userModel.get( "avatarSrc" ));
};

/**
 * Renders the contents of the picker and displays it.
 */
Avatar.Picker.prototype.show = function() {
    if ( !this.el ) {
        var rootJel = $("<div class='avatar-picker modal fade hide'></div>");
        var contentJel = $("<div class='modal-body avatar-picker-contents'></div>");
        rootJel.append(contentJel).appendTo(document.body);
        this.el = rootJel.get( 0 );
        this.contentEl = contentJel.get( 0 );
        this.bindEvents_();
    }

    $(this.contentEl).html(
            Avatar.Picker.template( this.getTemplateContext_() ));
    $(this.el).modal({
        keyboard: true,
        backdrop: true,
        show: true
    });
};
