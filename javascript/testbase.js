/**
 * Base utilities for running a JavaScript Unit Test, or demo file.
 */

var KA_TEST = {
    BASE_PATH_: "",

    computeBasePath: function() {
        var doc = window.document;
        var scripts = doc.getElementsByTagName("script");
        // Search backwards since the current script is in almost all cases the one
        // that has testbase.js.
        for (var i = scripts.length - 1; i >= 0; --i) {
            var src = scripts[i].src;
            if (src.substr(src.length - 11, 11) == "testbase.js") {
                return src.substr(0, src.length - 11);
            }
        }
        return null;
    },

    /**
     * Injects a script into the page.
     * @param {string} path The relative path to the script with trailing "/"
     * @param {string} name The name of the script with the ".js" suffix
     */
    writeScript: function(path, name) {
        document.write("<script src=\"" + path + name + "\"></script>");
    },

    init: function() {
        var basePath = this.BASE_PATH_ = this.computeBasePath();
        if (basePath === null) {
            // Error - it should be an empty string if anything.
            console.log("Can't compute the base path for the test");
        }
        var sharedPackagePath = basePath + "/shared-package/";

        // Write out some common utilities which are probably going to be
        // needed in most tests.
        this.writeScript(sharedPackagePath, "jquery.js");
        this.writeScript(sharedPackagePath, "jquery-ui-1.8.16.custom.js");
        this.writeScript(basePath + "../../khan-exercises/utils/",
                "underscore.js");
        this.writeScript(sharedPackagePath, "backbone.js");
        this.writeScript(sharedPackagePath, "handlebars.js");
        this.writeScript(sharedPackagePath, "templates.js");
    },

    /**
     * The list of templates that need to be loaded still.
     */
    outstandingTemplates: [],
    onTemplatesLoaded: function() {},

    /**
     * Load a single template asnychronously.
     */
    loadTemplateForTest: function(name) {
        var parts = name.split(".");
        var path = parts[0] + "-package/" + parts[1] + ".handlebars";
        $.ajax({
            type: "GET",
            url: KA_TEST.BASE_PATH_ + path,
            success: function(data) {
                var canonicalName = Templates.getCanonicalName(name);
                Templates.cache_[canonicalName] = Handlebars.compile(data);
                var index = $.inArray(name, KA_TEST.outstandingTemplates);
                if (index < 0) {
                    // Shouldn't happen!
                    return;
                }
                KA_TEST.outstandingTemplates.splice(index, 1);
                if (!KA_TEST.outstandingTemplates.length) {
                    KA_TEST.onTemplatesLoaded();
                }
            },
            error: function() {
                console.log("Can't load template " + name);
            }
        });
    },

    /**
     * Asynchronously loads templates from source and prepares them for the test.
     * This is needed since templates are compiled in production into a package, and
     * needs to be manually made available when requiring them in test code.
     * @param {string|Array.<string>} names The names of the templates to load
     * @param {Function} onLoaded The method to be executed once all templates are
     *     loaded. Typically, this is the code that renders the demo/tests.
     */
    loadTemplates: function(names, onLoaded) {
        if (typeof names === "String") {
            names = [names];
        }
        this.onTemplatesLoaded = onLoaded;
        this.outstandingTemplates = names;
        $.each(names, function(i, name) {
            KA_TEST.loadTemplateForTest(name);
        });
    }
};
KA_TEST.init();
