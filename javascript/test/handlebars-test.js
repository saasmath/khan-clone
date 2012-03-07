/**
 * Node.js script that is called by handlebars.py during unit tests.
 * Compiles & executes a Handlebars template, writing result to STDOUT.
 */
var fs = require("fs");
var handlebars = require("handlebars");

var sourceFile = process.argv[2];

var source = fs.readFileSync(sourceFile, "utf8");
var template = handlebars.compile(source);

var dataText = fs.readFileSync(process.argv[3], "utf8");
var dataParsed = JSON.parse(dataText);

var result = template(dataParsed);
console.log(result);
