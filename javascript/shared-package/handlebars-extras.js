// Only include element attributes if they have a value.
// etymology: optional attribute -> opttribute -> opttr
// example:
// var template = Handlebars.compile("<div {{opttr id=id class=class}}></div>");
// template({id: 'foo'})
// => '<div id="foo"></div>'
Handlebars.registerHelper("opttr", function(options) {
    var attrs = [];
    _.each(options.hash, function(v, k) {
        if (v !== null && v !== undefined) {
            attrs.push(k + '="' + Handlebars.Utils.escapeExpression(v) + '"');
        }
    });
    return new Handlebars.SafeString(attrs.join(" "));
});

Handlebars.registerHelper("repeat", function(n, options) {
    var fn = options.fn;
    var ret = "";

    for (var i = 0; i < n; i++) {
        ret = ret + fn();
    }

    return ret;
});

Handlebars.registerHelper("reverseEach", function(context, block) {
    var result = "";
    for (var i = context.length - 1; i >= 0; i--) {
        result += block(context[i]);
    }
    return result;
});

Handlebars.registerPartial("streak-bar", Templates.get("shared.streak-bar"));

/**
 * Create a redirect url that scores the specified conversions server-side.
 * Helpful for measuring click-through, since it is possible to navigate
 * away before the client-side gae_bingo.bingo POST goes through.
 * Try it in Safari if you don't believe me!
 *
 * Sample usage:
 * <a href="{{toBingoHref "/profile" "conversion_name" "other_conversion_name"}}>
 */
Handlebars.registerHelper("toBingoHref", function(destination) {
    var result = "/gae_bingo/redirect?continue=" + encodeURIComponent(destination);
    // Ignore the first argument (the destination)
    // and the last argument (options object that always gets
    // passed to Handlebars helpers)
    for (var i = 1; i < arguments.length - 1; i++) {
        result += "&cn_" + (i - 1) + "=" + arguments[i];
    }

    return result;
});

