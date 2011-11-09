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

Templates.cache_ = {};

Templates.fromScript_ = function( name ) {
	return Handlebars.compile( $("#template_" + name).html() );
}:

Templates.get = function( name ) {
	// Debug
	return Templates.cache_[name] ||
		(Templates.cache_[name] = Templates.fromScript_( name ));
};
