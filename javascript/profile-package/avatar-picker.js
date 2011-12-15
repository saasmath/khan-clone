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
 * @param {HTMLImageElement=} imageEl An optional image element that can be
 *     specified to attach the picker to.
 * @constructor
 */
Avatar.Picker = function(imageEl) {
    /**
     * The container element of the dialog.
     */
    this.el = null;

    /**
     * The root element of the dialog contents.
     */
    this.contentEl = null;

    /**
     * The image element that gets changed after a selection is made.
     */
    this.imageEl = imageEl;
    if ( imageEl ) {
        $(imageEl).hover( _.bind( this.onImageAnchorHover_, this ) );
        $(imageEl).click( _.bind( this.onImageAnchorClick_, this ) );
    }
};

Avatar.Picker.template = Templates.get( "profile.avatar-picker" );

/**
 * Handles a mouse hover to the anchor image.
 */
Avatar.Picker.prototype.onImageAnchorHover_ = function( ev ) {
    // TODO: show a "change profile pic" affordance
};

/**
 * Handles a click to the anchor image.
 */
Avatar.Picker.prototype.onImageAnchorClick_ = function( ev ) {
    this.render();
};

/**
 * Renders the contents of the picker and displays it.
 */
Avatar.Picker.prototype.getTemplateContext_ = function() {
    // Dummy data for now. Replace with the real thing.
    return {
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
};

/**
 * Handles a selection to an avatar in the list.
 */
Avatar.Picker.prototype.onAvatarSelected_ = function( ev ) {
    // TODO: handle
};

/**
 * Renders the contents of the picker and displays it.
 */
Avatar.Picker.prototype.render = function() {
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
