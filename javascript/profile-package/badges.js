/**
 * Code to handle badge-related UI components.
 */

var Badges = {};

/**
 * @enum {number}
 */
Badges.ContextType = {
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
	isOwned: function() {
		return this.has( "count" ) && this.get( "count" ) > 0;
	}
});

/**
 * Constructs a Badge object from server-sent JSON.
 */
Badges.Badge.fromServerJson = function( json ) {
	var attributeJson = {};
	for ( var attr in json ) {
		if ( attr === "kind" ) {
			continue;
		}

		// TODO: move to a utility method for a general pattern
		var camelCased = attr.replace(/_([a-z])/g, function( group ) {
			return group.substr(1).toUpperCase();
		});
		attributeJson[ camelCased ] = json[ attr ];
	}
	return new Badges.Badge( attributeJson );
};

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
	className: "badge-list",

	initialize: function() {
		// Addition or removal of a badge re-renders the whole list.
		this.model.bind( "add", this.render, this );
		this.model.bind( "remove", this.render, this );
		this.template = Templates.get( "profile.badge-display-case" );
	},

	getTemplateContext_: function() {
		var badges = [];
		this.model.each(function( badge ) {
			var json = badge.toJSON();
			json[ "isOwned" ] = badge.isOwned();
			badges.push( json );
		}, this);
		return { badges: badges };
	},

	render: function() {
		$(this.el).html( this.template( this.getTemplateContext_() ) );
		return this;
	}
});
