$(function() {

    $(".share-story-btn").click(function(e) {

        // Show story submission area
        $(".stories-submit")
            .slideToggle(function() {
                $(".stories-submit textarea").focus();
            })
            .find(".submit-story-btn")
                .html("Send us your story")
                .removeClass("disabled")
                .removeClass("success")
                .addClass("primary");

        e.preventDefault();
    });

    $(".submit-story-btn").click(function(e) {

        // Submit story
        if ($("#story").val().length) {

            $(this)
                .addClass("disabled")
                .html("Sending&hellip;");

            $.post(
                "/stories/submit",
                {
                    "story": $("#story").val(),
                    "name": $("#name").val(),
                    "share": $("#shareAllow").is(":checked") ? "1": "0"
                },
                function() {

                    $(".submit-story-btn")
                        .removeClass("primary")
                        .addClass("success")
                        .html("Success!");

                    // Close and clean up story submission area after delay
                    setTimeout(function() {
                        $(".stories-submit")
                            .slideUp()
                            .find("textarea")
                                .val("");
                    }, 3000);

                });

        }

        e.preventDefault();
    });

});
