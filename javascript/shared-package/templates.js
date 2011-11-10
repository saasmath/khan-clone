/**
 * A thin wrapper module to abstract away some of the details
 * of client side templates.
 *
 * In debug mode, templates are served as inline <script> tags so that they
 * can be dynamically updated without requiring a compilation step. Access to
 * these templates must be done by retrieving the template source from the DOM.
 * In production, these templates are pre-compiled into functions, and can
 * therefore be directly accessed.
 */

var Templates = {};

/**
 * Whether or not templates have need to be read from the DOM and compiled
 * at runtime.
 */
Templates.IS_DEBUG_ = !!Handlebars.compile;

/**
 * A cache of compiled templates, if runtime compilation is needed.
 */
Templates.cache_ = {};

/**
 * Compile a template from an inline script tag.
 */
Templates.fromScript_ = function( name ) {
	var jel = $("#template_" + name);
	if ( !jel.length ) {
		throw Error( "Can't find a template for [" + name  + "]" );
	}
	return Handlebars.compile( jel.html() );
};

/**
 * Retrieves a template function.
 * @param {string} name The name of the template to retrieve. This will be the
 *     base name of the template file with no extension.
 */
Templates.get = function( name ) {
	// Canonical format for the namespaced name uses underscores internally.
	name = name.replace( '.', '_' );

	if (Templates.IS_DEBUG_) {
		return Templates.cache_[name] ||
			(Templates.cache_[name] = Templates.fromScript_( name ));
	} else {
		return Handlebars.templates[name];
	}
};

