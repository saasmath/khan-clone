Handlebars.registerHelper("encodeURIComponent", function(str) {
    return encodeURIComponent(str);
});

Handlebars.registerHelper("commafy", function(numPoints) {
    // From KhanUtil.commafy in math-format.js
    return numPoints.toString().replace(/(\d)(?=(\d{3})+$)/g, "$1,");
});
