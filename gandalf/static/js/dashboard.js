var GandalfDashboard = {
    
    loadBridges: function() {
        $.ajax({
            url: "/gandalf/api/v1/bridges",
            dataType: "json",
            type: "GET",
            success: function(data) {

                var filterUpdateUrl = "/gandalf/api/v1/bridges/filters/update";
                var bridgeUpdateUrl = "/gandalf/api/v1/bridges/update";

                $("#progress-bar").css("visibility", "hidden");

                $("#main").append( $("#tmpl-bridges").mustache(data) );

                $("#main .bridge-container-minimized").click( function(e) {

                    // Already expanded
                    if (!$(this).is(".bridge-container-minimized")) {
                        return;
                    }
 
                    GandalfDashboard.loadFilters($(this).data("bridge-name"));

                    $(this)
                        .removeClass("bridge-container-minimized")
                        .find(".filters-container")
                            .empty()
                            .append($("#progress-bar").clone().css("visibility", "visible"))
                            .animate({height: 250}, 250);

                });

                // New bridge
                $("#bridge-new-form").submit(function(e) {

                    e.preventDefault();

                    bridgeName = $(this).find("[name=bridge_name]").val();

                    if (!bridgeName) {
                        alert("Enter a name for your new bridge.");
                        return;
                    }

                    $.post(bridgeUpdateUrl, $(this).serialize(), function(data) {
                        if (!data.success) {
                            if (data.error) {
                                alert(data.error);
                            } else {
                                alert("Something went wrong. Your new bridge was not created");
                            }
                            return;
                        }
                        window.location.reload();
                    });

                });


                // Disable bridge
                $(document).on("click", ".bridge-disable-button", function() {
                    var live = $(this).data("live");

                    $.post(bridgeUpdateUrl, {
                        live: live,
                        action: $(this).val(),
                        bridge_name: $(this).data("bridge-name")
                    }, function(data) {
                        if (!data.success) {
                            alert("Something went wrong. The bridge was not " + ((live === "true") ? "enabled" : "disabled") + ".");
                            return;
                        }
                        window.location.reload();
                    });
                });

                // Create a new filter
                $(document).on("submit", ".filter-new-form", function(e) {

                    e.preventDefault();

                    var submitButton = $(this).find(".filter-new-button");
                    var buttonHTML = submitButton.html();

                    var bridgeName = $(this).find("[name=bridge_name]").val();

                    $.post(filterUpdateUrl, $(this).serialize(), function(data) {
                        if (!data.success) { 
                            alert("Something went wrong. Unable to create new filter.");
                        }

                        $( "div.bridge-container[data-bridge-name=\"" + bridgeName + "\"] .filters-container" )
                            .empty()
                            .append($("#progress-bar").clone().css("visibility", "visible"))
                            .animate({height: 250}, 250);

                        GandalfDashboard.loadFilters(bridgeName);

                        submitButton.html(buttonHTML);
                    });

                    submitButton.html(submitButton.data("replace-with"));
                });


                // Save a filter
                $(document).on("submit", ".filter-update-form", function(e) {

                    e.preventDefault();

                    var submitButton = $(this).find(".filter-save-button");
                    var buttonHTML = submitButton.html();

                    $.post(filterUpdateUrl, $(this).serialize(), function(data) {
                        if (!data.success) { 
                            alert("Something went wrong. Your changes were not saved.");
                        }

                        submitButton.html(buttonHTML);
                        alert("Filter saved.");
                    });

                    submitButton.html(submitButton.data("replace-with"));
                });


                // Delete a filter
                $(document).on("click", ".filter-delete-button", function(e) {

                    e.preventDefault();

                    if (!confirm("Are you sure you want to delete this filter? This cannot be undone.")) {
                        return;
                    }

                    var filterContainer = $(this).parents(".filter-container");

                    $.post(filterUpdateUrl, {
                        filter_key: $(this).data("filter-key"),
                        action: $(this).val()
                    }, function(data) {
                        if (!data.success) {
                            alert("Something went wrong. The filter was not deleted.");
                            return;
                        }

                        var height = filterContainer.height();

                        filterContainer
                            .empty()
                            .height(height)
                            .animate({height: 0}, 500);
                    });

                    $(this).replaceWith($(this).data("replace-with"));

                });
            }
        });
    },

    loadFilters: function(bridgeName) {
        $.ajax({
            url: "/gandalf/api/v1/bridges/filters",
            data: { bridge_name: bridgeName },
            dataType: "json",
            type: "GET",
            success: function(data) {

                // Template the html of each filter with its own context
                for(var i = 0; i < data.filters.length; i++) {
                    data.filters[i].html = Mustache.to_html(data.filters[i].html, data.filters[i].context);
                }

                var filtersContainer = $( "div.bridge-container[data-bridge-name=\"" + bridgeName + "\"] .filters-container" );

                filtersContainer
                    .css("min-height", filtersContainer.height())
                    .stop()
                    .height("")
                    .html( $( "#tmpl-filters" ).mustache( data ) );

            }
        });
    },

}

$(GandalfDashboard.loadBridges);
