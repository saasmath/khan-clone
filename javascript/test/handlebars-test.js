/**
 * Node.js script that is called by handlebars.py during unit tests.
 * Compiles & executes a Handlebars template, writing result to STDOUT.
 */
var fs = require("fs");
Handlebars = require("handlebars");
Templates = { get: function() { return null; } }; // For a registerPartial call
require("../shared-package/handlebars-extras.js");
require("../profile-package/handlebars-helpers.js");

var sourceFile = process.argv[2];

var source = fs.readFileSync(sourceFile, "utf8");

var partials = {};

function importPartials(source) {
    var partialRegExp = /{{>[\s]*([\w-_]+)[\s]*}}/g
    var partial;
    do {
        partial = partialRegExp.exec(source);
        if (partial) {
            if (!partials[partial[1]]) {
                var sp = partial[1].split("_");
                var package = sp[0];
                var name = sp[1];
                var filename = "javascript/" + package + "-package/" + name + ".handlebars";

                var partialSource = fs.readFileSync(filename, "utf8");
                Handlebars.registerPartial(partial[1], Handlebars.compile(partialSource));
                partials[partial[1]] = true;

                importPartials(partialSource);
            }
        }
    } while (partial);
}

importPartials(source);

var template = Handlebars.compile(source);

var dataText = fs.readFileSync(process.argv[3], "utf8");
var dataParsed = JSON.parse(dataText);

try {
    var result = template(dataParsed);
    console.log(result);
} catch (e) {
    console.log("Exception thrown: " + e);
}
