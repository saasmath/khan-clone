/**
 * Generic utilities related to keyboard handling and input event listneing.
 */


// Namespace
var Keys = {};


/**
 * Conservatively determines if a key event is a text modifying key event.
 * Reads values "as-is" from the "keyCode" property, and does little to
 * resolve cross-browser differences among the values. Leans towards
 * "yes - it is a modifying event" if unknown.
 */
Keys.isTextModifyingKeyEvent_ = function(e) {
    if ((e.altKey && !e.ctrlKey) || e.metaKey ||
            // Function keys don't generate text
            e.keyCode >= 112 && e.keyCode <= 123) {
        return false;
    }

    switch (e.keyCode) {
        case $.ui.keyCode.ALT:
        case $.ui.keyCode.CAPS_LOCK:
        case $.ui.keyCode.COMMAND:
        case $.ui.keyCode.COMMAND_LEFT:
        case $.ui.keyCode.COMMAND_RIGHT:
        case $.ui.keyCode.CONTROL:
        case $.ui.keyCode.DOWN:
        case $.ui.keyCode.END:
        case $.ui.keyCode.ESCAPE:
        case $.ui.keyCode.HOME:
        case $.ui.keyCode.INSERT:
        case $.ui.keyCode.LEFT:
        case $.ui.keyCode.MENU:
        case $.ui.keyCode.PAGE_DOWN:
        case $.ui.keyCode.PAGE_UP:
        case $.ui.keyCode.RIGHT:
        case $.ui.keyCode.SHIFT:
        case $.ui.keyCode.UP:
        case $.ui.keyCode.WINDOWS:
            return false;
        default:
            return true;
    }
};


/**
 * A space-separated list of event names appropriate for indication for
 * when a text-change event occured.
 *
 * Note that the HTML5 "input" event is the best way to do this, but it is
 * not supported in IE, so it's approximated by similar events (though isn't
 * perfect. e.g. it doesn't handle holding down a button and having a repeated
 * character fire repeated events)
 * @type {string}
 */
Keys.textChangeEvents = $.browser.msie ? "keyup paste cut drop" : "input";


/**
 * Delegate input events.
 * Uses 'input' events, when availabe, but approximates it in browsers with
 * no full support for it (see Keys.textChangeEvents).
 * @param {jQuery} jel The jQuery element to delegate events for.
 * @param {string} selector The selector that the events apply to.
 * @param {Function} handler The event handler.
 * @param {Object} context An optional context to call the handler for.
 */
Keys.delegateInputChange = function(jel, selector, handler, context) {
    var wrapped = function(e) {
        if (!Keys.isTextModifyingKeyEvent_(e)) {
            return;
        }
        handler.call(context || this, e);
    };
    jel.on(Keys.textChangeEvents, selector, undefined, wrapped);
};
