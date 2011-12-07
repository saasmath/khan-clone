/**
 * Code to handle badge-related UI components.
 */

var Badges = {};

/**
 * @enum {number}
 */
Badges.ContextType = {
	NONE: 0,
	EXERCISE: 1,
	PLAYLIST: 2
};

/**
 * @enum {number}
 */
Badges.Category = {
	BRONZE: 0, // Meteorite, "Common"
	SILVER: 1, // Moon, "Uncommon"
	GOLD: 2, // Earth, "Rare"
	PLATINUM: 3, // Sun, "Epic"
	DIAMOND: 4, // Black Hole, "Legendary"
	MASTER: 5 // Summative/Academic Achievement
};

/**
 * A single badge that a user can earn.
 */
Badges.Badge = Backbone.Model.extend({
	defaults: {
		"badgeCategory": Badges.Category.BRONZE,
		"badgeContextType": Badges.ContextType.NONE,
		"name": "",
		"description": "",
		"iconSrc": "",
		"isOwned": false,
		"points": 0,
		"safeExtendedDescription": "",
		"typeLabel": ""
	},

	isOwned: function() {
		return this.has( "count" ) && this.get( "count" ) > 0;
	}
});

/**
 * Badge information about a badge that a user has earned.
 * This is a superset of Badges.Badge.
 */
Badges.UserBadge = Badges.Badge.extend({
	defaults: _.extend({
		"count": 4,
		"date": "2011-11-22T02:59:43Z",
		"isUserBadge": true,
		"listContextNames": [],
		"listContextNamesHidden": [],
		"targetContextName": ""
	}, Badges.Badge.defaults)
});

/**
 * A list of badges that can be listened to.
 */
Badges.BadgeList = Backbone.Collection.extend({
	model: this.Badge
});

/**
 * A UI component that displays a list of badges to show off.
 * Typically used in a public profile page, but can be re-used
 * in the context of a hovercard, or any other context.
 */
Badges.DisplayCase = Backbone.View.extend({
	className: "badge-display-case",

	/**
	 * Whether or not this is currently in edit mode.
	 */
	editing: false,

	/**
	 * The full badge list available to pick from when in edit mode.
	 */
	fullBadgeList: null,

	/**
	 * The number of slots available in the display case.
	 */
	maxVisible: 5,

	/**
	 * The slot number being edited. Any selection from the badge picker
	 * will replace the badge in this slot number.
	 * -1 if not currently editing.
	 */
	selectedIndex: -1,

	mainCaseEl: null,
	badgePickerEl: null,

	initialize: function() {
		this.model.bind( "add", this.render, this );
		this.model.bind( "remove", this.render, this );
		this.model.bind( "change", this.render, this );
		this.template = Templates.get( "profile.badge-display-case" );

		// TODO: register in some central intializing point?
		Handlebars.registerPartial(
			"badge-compact",
			Templates.get( "profile.badge-compact" )
		);
	},

	/**
	 * @return {boolean} Whether or not this display case can go into "edit" mode
	 *		to allow a user to select which badges go inside.
	 */
	isEditable: function() {
		return !!this.fullBadgeList;
	},

	/**
	 * Sets the full badge list for the display case so it can go into edit
	 * mode and pick badges from this badge list.
	 * @param {Badges.BadgeList} The full list of badges that can be added
	 *		to this display case.
	 * @return {Badges.DisplayCase} This same instance so calls can be chained.
	 */
	setFullBadgelist: function( fullBadgeList ) {
		// TODO: do we want to listen to events on the full badge list?
		this.fullBadgeList = fullBadgeList;
	},

	/**
	 * Enters "edit mode" where badges can be added/removed, if possible.
	 * @param {number=} index Optional index of the slot in the display-case
	 *		to be edited. Defaults to the first available slot, or if none
	 *		are available, the last used slot.
	 * @return {Badges.DisplayCase} This same instance so calls can be chained.
	 */
	edit: function( index ) {
		if ( !this.isEditable() || this.editing ) {
			return this;
		}

		this.editing = true;

		// Visual indicator for the badge edits.
		var self = this;
		$(".achievement-badge", this.mainCaseEl).animate({
			"margin": "5px"
		}, "fast", function() {
			$(self.el).addClass( "editing" );
			self.updateEditSelection_( index );
		});

		this.showBadgePicker_();
		$(this.badgePickerEl).delegate(
				".achievement-badge",
				"click",
				_.bind( this.onBadgeInPickerClicked_, this ));
		$(this.mainCaseEl).delegate(
				".achievement-badge",
				"click",
				_.bind( this.onBadgeClicked_, this ));
	},

	/**
	 * Updates the editor so that the badge at the specified index is
	 * being edited. If no index is specified, the last possible spot
	 * is selected by default.
	 * @param {number=} index Optional index of the slot in the display-case
	 *		to be edited. -1 to indicate that none should be selected (i.e.
	 *		we're exiting edit mode.
	 */
	updateEditSelection_: function( index ) {
		// By default, select the first empty slot, or the last non-empty
		// slot if completely full.
		index = ( index === undefined ) ? this.model.length : index;
		var max = Math.min( this.model.length, this.maxVisible - 1);
		this.selectedIndex = Math.min( index, max );
		this.updateSelectionHighlight();
	},

	/**
	 * Shows the badge picker for edit mode, if not already visible.
	 * This view must have already have been rendered once.
	 */
	showBadgePicker_: function() {
		this.renderBadgePicker();
		var jelPicker = $(this.badgePickerEl);
		jelPicker.slideDown( "fast", function() { jelPicker.show(); })
			.css( "margin-left", "300px" )
			.animate({ "margin-left": "0" }, "fast", $.easing.easeInOutCubic);

		return this;
	},

	/**
	 * Handles a click to a badge in the main display case.
	 */
	onBadgeClicked_: function( e ) {
		if ( !this.editing ) {
			// Noop when not editing.
			return;
		}
		var index = $(".achievement-badge", this.mainCaseEl).index( e.currentTarget );
		this.updateEditSelection_( index );
	},

	/**
	 * Handles a click to a badge in the badge picker in edit mode.
	 */
	onBadgeInPickerClicked_: function( e ) {
		var name = e.currentTarget.id;
		var matchedBadge = _.find(
				this.fullBadgeList.models,
				function( badge ) {
					return badge.get( "name" ) == name;
				});
		if ( !matchedBadge ) {
			// Shouldn't happen!
			return;
		}

		// Backbone.Collection doesn't have a .replce method - do it ourselves
		// TODO: should we be cloning?
		var existing = this.model.at( this.selectedIndex );
		if ( existing ) {
			this.model.remove( existing );
		}
		this.model.add( matchedBadge.clone(), { at: this.selectedIndex });
	},

	/**
	 * Exits edit mode.
	 */
	stopEdit: function() {
		if ( this.editing ) {
			this.editing = false;
			this.updateEditSelection_( -1 );
			var jelMainCase = $(this.mainCaseEl);
			var jelPicker = $(this.badgePickerEl);
			jelPicker.slideUp("fast", function() {
				jelMainCase.removeClass( "editing" );
			});
			jelPicker.undelegate();
		}
		return this;
	},

	/**
	 * Builds a context object to render a single badge.
	 */
	getBadgeJsonContext_: function( badge ) {
		var json = badge.toJSON();
		json[ "isOwned" ] = badge.isOwned();
		return json;
	},

	/**
	 * Gets the handlebars template context for the main display-case element.
	 */
	getTemplateContext_: function() {
		var i,
			badges = [],
			numRendered = Math.min( this.maxVisible, this.model.length );
		for ( i = 0; i < numRendered; i++ ) {
			var badge = this.model.at( i );
			badges.push( this.getBadgeJsonContext_( badge ));
		}
		for ( ; i < this.maxVisible; i++ ) {
			badges.push({ emptyBadge: true });
		}
		return { badges: badges };
	},

	/**
	 * Updates the appropriate badge being highlighted for edit mode.
	 * See {@link #selectedIndex} for more details.
	 */
	updateSelectionHighlight: function() {
		var badgeSlots = $(".achievement-badge", this.mainCaseEl);
		badgeSlots.removeClass( "selected" );
		if ( this.selectedIndex > -1 ) {
			$(badgeSlots[ this.selectedIndex ]).addClass( "selected" );
		}
	},

	/**
	 * Renders the contents of the badge picker.
	 * Idempotent - simply blows away and repopulates the contents if called
	 * multiple times.
	 */
	renderBadgePicker: function() {
		var html = [],
			badgeTemplate = Templates.get( "profile.badge-compact" );
		this.fullBadgeList.each(function( badge ) {
			html.push( badgeTemplate( this.getBadgeJsonContext_( badge )));
		}, this);
		$(this.badgePickerEl).html( html.join( "" ) );
	},

	render: function() {
		if ( !this.mainCaseEl ) {
			// First render - build the chrome.
			this.mainCaseEl = $("<div class=\"main-case\"></div>");
			this.badgePickerEl = $("<div class=\"badge-picker\"></div>");
			$(this.el).append(this.mainCaseEl).append(this.badgePickerEl);
		}
		$(this.mainCaseEl).html( this.template( this.getTemplateContext_() ) );
		this.updateSelectionHighlight();
		return this;
	}
});
