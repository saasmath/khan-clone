var KAConsole = {
    debugEnabled: false,
    oldMessages: [],

    log: function() {
        if (window.console && KAConsole.debugEnabled) {
            if (console.log.apply)
                console.log.apply(console, arguments);
            else
                Function.prototype.apply.call(console.log, null, arguments);
        } else {
            this.oldMessages.push(arguments);
        }
    },

    enableLog: function() {
        if (window.console) {
            this.debugEnabled = true;
            _.each(this.oldMessages, function(args) {
                if (console.log.apply)
                    console.log.apply(console, args);
                else
                    Function.prototype.apply.call(console.log, null, args);
            });
        }
    }
};

function addCommas(nStr) // to show clean number format for "people learning right now" -- no built in JS function
{
    nStr += "";
    var x = nStr.split(".");
    var x1 = x[0];
    var x2 = x.length > 1 ? "." + x[1] : "";
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(x1)) {
        x1 = x1.replace(rgx, "$1" + "," + "$2");
    }
    return x1 + x2;
}

function validateEmail(sEmail)
{
     var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
     return sEmail.match(re);
}

function addAutocompleteMatchToList(list, match, kind, reMatch) {
    var o = {
                "label": (kind == 'exercise') ? match.display_name : match.title,
                "title": (kind == 'exercise') ? match.display_name : match.title,
                "value": match.relative_url || match.ka_url,
                "key": match.key,
                "kind": kind
            };

    if (reMatch)
        o.label = o.label.replace(reMatch, "<b>$1</b>");

    list[list.length] = o;
}

function initAutocomplete(selector, fTopics, fxnSelect, fIgnoreSubmitOnEnter, options)
{
    options = $.extend({
        includeVideos: true,
        includeExercises: true,
        addTypePrefix: true
    }, options);
    var autocompleteWidget = $(selector).autocomplete({
        delay: 150,
        source: function(req, fxnCallback) {

            var term = $.trim(req.term);
            if (!term) {
                fxnCallback([]);
                return;
            }

            // Get autocomplete matches
            $.getJSON("/api/v1/autocomplete", {"q": term}, function(data) {

                var matches = [];

                if (data != null)
                {
                    var reMatch = null;

                    // Try to find the "scent" of the match.  If regexp fails
                    // to compile for any input reason, ignore.
                    try {
                        reMatch = new RegExp("(" + data.query + ")", "i");
                    }
                    catch (e) {
                        reMatch = null;
                    }

                    // Add topic and video matches to list of autocomplete suggestions

                    if (fTopics) {
                        for (var ix = 0; ix < data.topics.length; ix++) {
                            addAutocompleteMatchToList(matches, data.topics[ix], "topic", reMatch);
                        }
                    }
                    if (options.includeVideos) {
                        for (var ix = 0; ix < data.videos.length; ix++) {
                            addAutocompleteMatchToList(matches, data.videos[ix], "video", reMatch);
                        }
                    }
                    if (options.includeExercises) {
                        for (var ix = 0; ix < data.exercises.length; ix++) {
                            addAutocompleteMatchToList(matches, data.exercises[ix], "exercise", reMatch);
                        }
                    }
                }

                fxnCallback(matches);

            });
        },
        focus: function() {
            return false;
        },
        select: function(e, ui) {
            if (fxnSelect)
                fxnSelect(ui.item);
            else
                window.location = ui.item.value;
            return false;
        },
        open: function(e, ui) {
            var jelMenu = $(autocompleteWidget.data("autocomplete").menu.element);
            var jelInput = $(this);

            var pxRightMenu = jelMenu.offset().right + jelMenu.outerWidth();
            var pxRightInput = jelInput.offset().right + jelInput.outerWidth();

            if (pxRightMenu > pxRightInput)
            {
                // Keep right side of search input and autocomplete menu aligned
                jelMenu.offset({
                                    right: pxRightInput - jelMenu.outerWidth(),
                                    top: jelMenu.offset().top
                                });
            }
        }
    }).bind("keydown.autocomplete", function(e) {
        if (!fIgnoreSubmitOnEnter && e.keyCode == $.ui.keyCode.ENTER || e.keyCode == $.ui.keyCode.NUMPAD_ENTER)
        {
            if (!autocompleteWidget.data("autocomplete").selectedItem)
            {
                // If enter is pressed and no item is selected, default autocomplete behavior
                // is to do nothing.  We don't want this behavior, we want to fall back to search.
                $(this.form).submit();
            }
        }
    });

    autocompleteWidget.data("autocomplete")._renderItem = function(ul, item) {
        // Customize the display of autocomplete suggestions
        var jLink = $("<a></a>").html(item.label);
        if (options.addTypePrefix) {
            var prefixSpan = $("<span>").prependTo(jLink);
            if (item.kind === "topic") {
                prefixSpan.addClass("autocomplete-topic").text("Topic ");
            } else if (item.kind === "video") {
                prefixSpan.addClass("autocomplete-video").text("Video ");
            } else if (item.kind === "exercise") {
                prefixSpan.addClass("autocomplete-exercise").text("Exercise ");
            }
        }

        jLink.attr("data-tag", "Autocomplete");

        return $("<li></li>")
            .data("item.autocomplete", item)
            .append(jLink)
            .appendTo(ul);
    };

    autocompleteWidget.data("autocomplete").menu.select = function(e) {
        // jquery-ui.js's ui.autocomplete widget relies on an implementation of ui.menu
        // that is overridden by our jquery.ui.menu.js.  We need to trigger "selected"
        // here for this specific autocomplete box, not "select."
        this._trigger("selected", e, { item: this.active });
    };
}

$(function() {
    // Configure the search form
    if ($(".page-search input[type=text]").placeholder().length) {
        initAutocomplete(".page-search input[type=text]", true);
    }

    $(".page-search").submit(function(e) {
        // Only allow submission if there is a non-empty query.
        return !!$.trim($(this).find("input[type=text]").val());
    });

    var jelToggle = $("#user-info .dropdown-toggle");

    if (jelToggle.length) {
        if (KA.isMobileCapable) {
            // Open dropdown on click
            jelToggle.dropdown();
        } else {
            // Open dropdown on hover
            jelToggle.dropdown("hover");
        }
    }
});

var Badges = {

    show: function(sBadgeContainerHtml) {
        var jel = $(".badge-award-container");

        if (sBadgeContainerHtml)
        {
            jel.remove();
            $("body").append(sBadgeContainerHtml);
            jel = $(".badge-award-container");
        }

        if (!jel.length) return;

        $(".achievement-badge", jel).click(function() {
            window.location = KA.profileRoot + "achievements";
            return false;
        });

        var jelTarget = $(".badge-target");
        var jelContainer = $("#page-container-inner");

        var top = jelTarget.offset().top + jelTarget.height() + 5;

        setTimeout(function() {
            jel.css("visibility", "hidden").css("display", "");
            jel.css("left", jelContainer.offset().left + (jelContainer.width() / 2) - (jel.width() / 2)).css("top", -1 * jel.height());
            var topBounce = top + 10;
            jel.css("display", "").css("visibility", "visible");
            jel.animate({top: topBounce}, 300, function() {jel.animate({top: top}, 100);});
        }, 100);
    },

    hide: function() {
        var jel = $(".badge-award-container");
        jel.animate({top: -1 * jel.height()}, 500, function() {jel.hide();});
    },

    showMoreContext: function(el) {
        var jelLink = $(el).parents(".badge-context-hidden-link");
        var jelBadge = jelLink.parents(".achievement-badge");
        var jelContext = $(".badge-context-hidden", jelBadge);

        if (jelLink.length && jelBadge.length && jelContext.length)
        {
            $(".ellipsis", jelLink).remove();
            jelLink.html(jelLink.text());
            jelContext.css("display", "");
            jelBadge.find(".achievement-desc").addClass("expanded");
            jelBadge.css("min-height", jelBadge.css("height")).css("height", "auto");
            jelBadge.nextAll(".achievement-badge").first().css("clear", "both");
        }
    }
};

var Notifications = {

    show: function(sNotificationContainerHtml) {
        var jel = $(".notification-bar");

        if (sNotificationContainerHtml)
        {
            var jelNew = $(sNotificationContainerHtml);
            jel.empty().append(jelNew.children());
        }

        $(".notification-bar-close a").click(function() {
            Notifications.hide();
            return false;
        });

        if (!jel.is(":visible")) {
            setTimeout(function() {

                jel
                    .css("visibility", "hidden")
                    .css("display", "")
                    .css("top", -jel.height() - 2) // 2 for border and outline
                    .css("visibility", "visible");

                // Queue:false to make sure all of these run at the same time
                var animationOptions = {duration: 350, queue: false};

                $(".notification-bar-spacer").animate({ height: 35 }, animationOptions);
                jel.show().animate({ top: 0 }, animationOptions);

            }, 100);
        }
    },
    showTemplate: function(templateName) {
        var template = Templates.get(templateName);
        this.show(template());
    },

    hide: function() {
        var jel = $(".notification-bar");

        // Queue:false to make sure all of these run at the same time
        var animationOptions = {duration: 350, queue: false};

        $(".notification-bar-spacer").animate({ height: 0 }, animationOptions);
        jel.animate(
                { top: -jel.height() - 2 }, // 2 for border and outline
                $.extend({}, animationOptions,
                    { complete: function() { jel.empty().css("display", "none"); } }
                )
        );

        $.post("/notifierclose");
    }
};

var DemoNotifications = { // for demo-notification-bar (brown and orange, which informs to logout after demo

    show: function(sNotificationContainerHtml) {
        var jel = $(".demo-notification-bar");

        if (sNotificationContainerHtml)
        {
            var jelNew = $(sNotificationContainerHtml);
            jel.empty().append(jelNew.children());
        }

        if (!jel.is(":visible")) {
            setTimeout(function() {

                jel
                    .css("visibility", "hidden")
                    .css("display", "")
                    .css("top", -jel.height() - 2) // 2 for border and outline
                    .css("visibility", "visible");

                // Queue:false to make sure all of these run at the same time
                var animationOptions = {duration: 350, queue: false};

                $(".notification-bar-spacer").animate({ height: 35 }, animationOptions);
                jel.show().animate({ top: 0 }, animationOptions);

            }, 100);
        }
    }
};

var Timezone = {
    tz_offset: null,

    append_tz_offset_query_param: function(href) {
        if (href.indexOf("?") > -1)
            href += "&";
        else
            href += "?";
        return href + "tz_offset=" + Timezone.get_tz_offset();
    },

    get_tz_offset: function() {
        if (this.tz_offset == null)
            this.tz_offset = -1 * (new Date()).getTimezoneOffset();
        return this.tz_offset;
    }
};

// not every browser has Date.prototype.toISOString
// https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Date#Example.3a_ISO_8601_formatted_dates
if (!Date.prototype.toISOString) {
    Date.prototype.toISOString = function() {
        var pad = function(n) { return n < 10 ? "0" + n : n; };
            return this.getUTCFullYear() + "-" +
                pad(this.getUTCMonth() + 1) + "-" +
                pad(this.getUTCDate()) + "T" +
                pad(this.getUTCHours()) + ":" +
                pad(this.getUTCMinutes()) + ":" +
                pad(this.getUTCSeconds()) + "Z";
    };
}

// some browsers can't parse ISO 8601 with Date.parse
// http://anentropic.wordpress.com/2009/06/25/javascript-iso8601-parser-and-pretty-dates/
var parseISO8601 = function(str) {
    // we assume str is a UTC date ending in 'Z'
    var parts = str.split("T"),
        dateParts = parts[0].split("-"),
        timeParts = parts[1].split("Z"),
        timeSubParts = timeParts[0].split(":"),
        timeSecParts = timeSubParts[2].split("."),
        timeHours = Number(timeSubParts[0]),
        _date = new Date();

    _date.setUTCFullYear(Number(dateParts[0]));
    _date.setUTCMonth(Number(dateParts[1]) - 1);
    _date.setUTCDate(Number(dateParts[2]));
    _date.setUTCHours(Number(timeHours));
    _date.setUTCMinutes(Number(timeSubParts[1]));
    _date.setUTCSeconds(Number(timeSecParts[0]));
    if (timeSecParts[1]) {
        _date.setUTCMilliseconds(Number(timeSecParts[1]));
    }

    // by using setUTC methods the date has already been converted to local time(?)
    return _date;
};

var MailingList = {
    init: function(sIdList) {
        var jelMailingListContainer = $("#mailing_list_container_" + sIdList);
        var jelMailingList = $("form", jelMailingListContainer);
        var jelEmail = $(".email", jelMailingList);

        jelEmail.placeholder().change(function() {
            $(".error", jelMailingListContainer).css("display", (!$(this).val() || validateEmail($(this).val())) ? "none" : "");
        }).keypress(function() {
            if ($(".error", jelMailingListContainer).is(":visible") && validateEmail($(this).val()))
                $(".error", jelMailingListContainer).css("display", "none");
        });

        jelMailingList.submit(function(e) {
            if (validateEmail(jelEmail.val()))
            {
                $.post("/mailing-lists/subscribe", {list_id: sIdList, email: jelEmail.val()});
                jelMailingListContainer.html("<p>Done!</p>");
            }
            e.preventDefault();
            return false;
        });
    }
};

var CSSMenus = {

    active_menu: null,

    init: function() {
        // Make the CSS-only menus click-activated
        $(".noscript").removeClass("noscript");
        $(document).delegate(".css-menu > ul > li", "click", function() {
            if (CSSMenus.active_menu)
                CSSMenus.active_menu.removeClass("css-menu-js-hover");

            if (CSSMenus.active_menu && this == CSSMenus.active_menu[0])
                CSSMenus.active_menu = null;
            else
                CSSMenus.active_menu = $(this).addClass("css-menu-js-hover");
        });

        $(document).bind("click focusin", function(e) {
            if (CSSMenus.active_menu &&
                $(e.target).closest(".css-menu").length === 0) {
                CSSMenus.active_menu.removeClass("css-menu-js-hover");
                CSSMenus.active_menu = null;
            }
        });

        // Make the CSS-only menus keyboard-accessible
        $(document).delegate(".css-menu a", {
            focus: function(e) {
                $(e.target)
                    .addClass("css-menu-js-hover")
                    .closest(".css-menu > ul > li")
                        .addClass("css-menu-js-hover");
            },
            blur: function(e) {
                $(e.target)
                    .removeClass("css-menu-js-hover")
                    .closest(".css-menu > ul > li")
                        .removeClass("css-menu-js-hover");
            }
        });
    }
};
$(CSSMenus.init);

var IEHtml5 = {
    init: function() {
        // Create a dummy version of each HTML5 element we use so that IE 6-8 can style them.
        var html5elements = ["header", "footer", "nav", "article", "section", "menu"];
        for (var i = 0; i < html5elements.length; i++) {
            document.createElement(html5elements[i]);
        }
   }
};
IEHtml5.init();

var VideoViews = {
    init: function() {
        // Fit calculated early Feb 2012
        var estimatedTotalViews = -4.792993409561827e9 + 3.6966675231488018e-3 * (+new Date());

        var totalViewsString = addCommas("" + Math.round(estimatedTotalViews));

        $("#page_num_visitors").append(totalViewsString);
        $("#page_visitors").css("display", "inline");
    }
};
$(VideoViews.init);


var Throbber = {
    jElement: null,

    show: function(jTarget, fOnLeft) {
        if (!Throbber.jElement)
        {
            Throbber.jElement = $("<img style='display:none;' src='/images/throbber.gif' class='throbber'/>");
            $(document.body).append(Throbber.jElement);
        }

        if (!jTarget.length) return;

        var offset = jTarget.offset();

        var top = offset.top + (jTarget.height() / 2) - 8;
        var left = fOnLeft ? (offset.left - 16 - 4) : (offset.left + jTarget.width() + 4);

        Throbber.jElement.css("top", top).css("left", left).css("display", "");
    },

    hide: function() {
        if (Throbber.jElement) Throbber.jElement.css("display", "none");
    }
};

var SearchResultHighlight = {
    doReplace: function(word, element) {
        // Find all text elements
        textElements = $(element).contents().filter(function() { return this.nodeType != 1; });
        textElements.each(function(index, textElement) {
            var pos = textElement.data.toLowerCase().indexOf(word);
            if (pos >= 0) {
                // Split text element into three elements
                var highlightText = textElement.splitText(pos);
                highlightText.splitText(word.length);

                // Highlight the matching text
                $(highlightText).wrap('<span class="highlighted" />');
            }
        });
    },
    highlight: function(query) {
        $(".searchresulthighlight").each(function(index, element) {
            SearchResultHighlight.doReplace(query, element);
        });
    }
};

// This function detaches the passed in jQuery element and returns a function that re-attaches it
function temporaryDetachElement(element, fn, context) {
    var el, reattach;
    el = element.next();
    if (el.length > 0) {
        // This element belongs before some other element
        reattach = function() {
            element.insertBefore(el);
        };
    } else {
        // This element belongs at the end of the parent's child list
        el = element.parent();
        reattach = function() {
            element.appendTo(el);
        };
    }
    element.detach();
    var val = fn.call(context || this, element);
    reattach();
    return val;
}

var globalPopupDialog = {
    visible: false,
    bindings: false,

    // Size can be an array [width,height] to have an auto-centered dialog or null if the positioning is handled in CSS
    show: function(className, size, title, html, autoClose) {
        var css = (!size) ? {} : {
            position: "relative",
            width: size[0],
            height: size[1],
            marginLeft: (-0.5*size[0]).toFixed(0),
            marginTop: (-0.5*size[1] - 100).toFixed(0)
        }
        $("#popup-dialog")
            .hide()
            .find(".dialog-frame")
                .attr("class", "dialog-frame " + className)
                .attr('style', '') // clear style
                .css(css)
                .find(".description")
                    .html('<h3>' + title + '</h3>')
                    .end()
                .end()
            .find(".dialog-contents")
                .html(html)
                .end()
            .find(".close-button")
                .click(function() { globalPopupDialog.hide(); })
                .end()
            .show()

        if (autoClose && !globalPopupDialog.bindings) {
            // listen for escape key
            $(document).bind('keyup.popupdialog', function ( e ) {
                if ( e.which == 27 ) {
                    globalPopupDialog.hide();
                }
            });

            // close the goal dialog if user clicks elsewhere on page
            $('body').bind('click.popupdialog', function( e ) {
                if ( $(e.target).closest('.dialog-frame').length === 0 ) {
                    globalPopupDialog.hide();
                }
            });
            globalPopupDialog.bindings = true;
        } else if (!autoClose && globalPopupDialog.bindings) {
            $(document).unbind('keyup.popupdialog');
            $('body').unbind('click.popupdialog');
            globalPopupDialog.bindings = false;
        }

        globalPopupDialog.visible = true;
        return globalPopupDialog;
    },
    hide: function() {
        if (globalPopupDialog.visible) {
            $("#popup-dialog")
                .hide()
                .find(".dialog-contents")
                    .html('');

            if (globalPopupDialog.bindings) {
                $(document).unbind('keyup.popupdialog');
                $('body').unbind('click.popupdialog');
                globalPopupDialog.bindings = false;
            }

            globalPopupDialog.visible = false;
        }
        return globalPopupDialog;
    }
};

(function() {
    var messageBox = null;

    popupGenericMessageBox = function(options) {
        if (messageBox) {
            $(messageBox).modal('hide').remove();
        }

        options = _.extend({
            buttons: [
                { title: 'OK', action: hideGenericMessageBox }
            ]
        }, options);

        var template = Templates.get( "shared.generic-dialog" );
        messageBox = $(template(options)).appendTo(document.body).modal({
            keyboard: true,
            backdrop: true,
            show: true
        }).get(0);

        _.each(options.buttons, function(button) {
            $('.generic-button[data-id="' + button.title + '"]', $(messageBox)).click(button.action);
        });
    }

    hideGenericMessageBox = function() {
        if (messageBox) {
            $(messageBox).modal('hide');
        }
        messageBox = null;
    }
})();

function dynamicPackage(packageName, callback, manifest) {
    var self = this;
    this.files = [];
    this.progress = 0;
    this.last_progress = 0;

    dynamicPackageLoader.loadingPackages[packageName] = this;
    _.each(manifest, function(filename) {
        var file = {
            "filename": filename,
            "content": null,
            "evaled": false
        };
        self.files.push(file);
        $.ajax({
            type: "GET",
            url: filename,
            data: null,
            success: function(content) {
                            KAConsole.log("Received contents of " + filename);
                            file.content = content;

                            self.progress++;
                            callback("progress", self.progress / (2 * self.files.length));
                            self.last_progress = self.progress;
                        },
            error: function(xml, status, e) {
                            callback("failed");
                        },
            dataType: "html"
        });
    });

    this.checkComplete = function() {
        var waiting = false;
        _.each(this.files, function(file) {
            if (file.content) {
                if (!file.evaled) {
                    var script = document.createElement("script");
                    if (file.filename.indexOf(".handlebars") > 0)
                        script.type = "text/x-handlebars-template"; // This hasn't been tested
                    else
                        script.type = "text/javascript";

                    script.text = file.content;

                    var head = document.getElementsByTagName("head")[0] || document.documentElement;
                    head.appendChild(script);

                    file.evaled = true;
                    KAConsole.log("Evaled contents of " + file.filename);

                    self.progress++;
                }
            } else {
                waiting = true;
                return _.breaker;
            }
        });

        if (waiting) {
            if (self.progress != self.last_progress) {
                callback("progress", self.progress / (2 * self.files.length));
                self.last_progress = self.progress;
            }
            setTimeout(function() { self.checkComplete(); }, 500);
        } else {
            dynamicPackageLoader.loadedPackages[packageName] = true;
            delete dynamicPackageLoader.loadingPackages[packageName];
            callback("complete");
        }
    };

    this.checkComplete();
}

var dynamicPackageLoader = {
    loadedPackages: {},
    loadingPackages: {},
    currentFiles: [],

    load: function(packageName, callback, manifest) {
        if (this.loadedPackages[packageName]) {
            if (callback)
                callback(packageName);
        } else {
            new dynamicPackage(packageName, callback, manifest);
        }
    },

    packageLoaded: function(packageName) {
        return this.loadedPackages[packageName];
    },

    setPackageLoaded: function(packageName) {
        this.loadedPackages[packageName] = true;
    }
};

$(function() {
    $(document).delegate("input.blur-on-esc", "keyup", function(e, options) {
        if (options && options.silent) return;
        if (e.which == "27") {
            $(e.target).blur();
        }
    });
});

// An animation that grows a box shadow of the review hue
$.fx.step.reviewExplode = function(fx) {
    var val = fx.now + fx.unit;
    $(fx.elem).css("boxShadow",
        "0 0 " + val + " " + val + " " + "rgba(227, 93, 4, 0.2)");
};

var HeaderTopicBrowser = {
    topicBrowserData: null,
    rendered: false,

    init: function() {
        // Use hoverIntent to hide the dropdown (which handles the delay)
        // but it has to be set on the whole subheader so we still use
        // mouseenter to show it.
        var hoverIntentActive = false;
        $(".nav-subheader").hoverIntent({
            over: function() {
                hoverIntentActive = true;
            },
            out: function() {
                $(".nav-subheader .watch-link.dropdown-toggle").dropdown("close");
                hoverIntentActive = false;
            },
            timeout: 400
        });
        $(".nav-subheader .watch-link.dropdown-toggle")
            .on('mouseenter', function() {
                if (!HeaderTopicBrowser.rendered) {
                    HeaderTopicBrowser.render();
                }
                $(this).dropdown("open");
            })
            .on('mouseleave', function() {
                if (!hoverIntentActive) {
                    $(this).dropdown("close");
                }
            })
            .on('click', function() {
                location.href = $(this).attr("href");
            });
    },

    setData: function(topicBrowserData) {
        this.topicBrowserData = topicBrowserData;
    },

    hoverIntentHandlers: function(timeout, sensitivityX, setActive) {
        // Intentionally create one closure per <ul> level so each has
        // its own selected element
        
        // activeEl is the currently focused <li> element. The focus is
        // maintained until the out() function is called, even if other
        // <li> elements get an over() call.
        var activeEl = null;

        // nextEl is the element currently being hovered over in the case
        // that activeEl isn't giving up focus. When activeEl gives up
        // focus it moves to the current nextEl.
        var nextEl = null;

        return {
            over: function() {
                if (this == activeEl) {
                    return;
                }
                if (activeEl) {
                    // Don't grab focus until activeEl gives it up.
                    nextEl = this;
                } else {
                    // There is no activeEl, so grab focus now.
                    $(this).addClass("hover-active");
                    if (setActive) {
                        // Setting child-active overrides the hover CSS
                        $(".nav-subheader ul.topic-browser-menu")
                            .addClass("child-active")
                            .removeClass("none-active");
                    }
                    activeEl = this;
                }
            },
            out: function() {
                if (activeEl == this) {
                    $(this).removeClass("hover-active");
                    if (nextEl) {
                        // Transfer the focus to nextEl and keep child-active on
                        $(nextEl).addClass("hover-active");
                        activeEl = nextEl;
                        nextEl = null;
                    } else {
                        // Clear the focus
                        activeEl = null;
                        if (setActive) {
                            // Setting none-active re-enables the hover CSS
                            $(".nav-subheader ul.topic-browser-menu")
                                .removeClass("child-active")
                                .addClass("none-active");
                        }
                    }
                } else {
                    if (this == nextEl) {
                        // If this element was queued up for focus, clear it
                        // to prevent an element getting focus and never losing
                        // it.
                        nextEl = null;
                    }
                }
            },
            timeout: timeout,
            directionalSensitivityX: sensitivityX
        };
    },

    render: function() {
        if (this.topicBrowserData) {
            var template = Templates.get("shared.topic-browser-pulldown");
            var html = template({topics: this.topicBrowserData});
            var el = $(html);

            // Use hoverIntent to keep the menus selected/open
            // even if you temporarily leave the item bounds.
            el.children("li")
                .hoverIntent(this.hoverIntentHandlers(50, 0.5, true))
                .children("ul")
                    .children("li")
                        .hoverIntent(this.hoverIntentHandlers(0, 0, false))

            $("#sitewide-navigation .topic-browser-dropdown").append(el);

            this.rendered = true;
        }
    }
};

