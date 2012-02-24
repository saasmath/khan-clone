var Review = {
    REVIEW_DONE_HTML: "Review&nbsp;Done!",

    highlightDone: function() {
        if ($("#review-mode-title").hasClass("review-done")) {
            return;
        }

        var duration = 800;

        // Make the explosion flare overlap all other elements
        var overflowBefore = $("#container").css("overflow");
        $("#container").css("overflow", "visible")
            .delay(duration).queue(function() {
                $(this).css("overflow", overflowBefore);
            });

        // Review hue explosion
        $("#review-mode-title").stop().addClass("review-done").animate({
            reviewExplode: 200
        }, duration).queue(function() {
            $(this).removeAttr("style").addClass("post-animation");
        });

        // Temporarily change the color of the review done box to match the explosion
        $("#review-mode-title > div")
            .css("backgroundColor", "#F9DFCD")
            .delay(duration).queue(function() {
                $(this).removeAttr("style").addClass("review-done");
            });

        // Huge "REVIEW DONE!" text shrinks to fit in its box
        $("#review-mode-title h1").html(Review.REVIEW_DONE_HTML).css({
            fontSize: "100px",
            right: 0,
            position: "absolute"
        }).stop().animate({
            reviewGlow: 1,
            opacity: 1,
            fontSize: 30
        }, duration).queue(function() {
            $(this).removeAttr("style");
        });
    },

    initCounter: function(reviewsLeftCount) {
        var digits = "0 1 2 3 4 5 6 7 8 9 ";
        $("#review-counter-container")
            .find(".ones").text(new Array(10 + 1).join(digits)).end()
            .find(".tens").text(digits);
    },

    updateCounter: function(reviewsLeftCount) {

        // Spin the remaining reviews counter like a slot machine
        var reviewCounterElem = $("#review-counter-container"),
            reviewTitleElem = $("#review-mode-title"),
            oldCount = reviewCounterElem.data("counter") || 0,
            tens = Math.floor((reviewsLeftCount % 100) / 10),
            animationOptions = {
                duration: Math.log(1 + Math.abs(reviewsLeftCount - oldCount)) *
                    1000 * 0.5 + 0.2,
                easing: "easeInOutCubic"
            },
            lineHeight = parseInt(
                reviewCounterElem.children().css("lineHeight"), 10);

        reviewCounterElem.find(".ones").animate({
            top: (reviewsLeftCount % 100) * -lineHeight
        }, animationOptions);

        reviewCounterElem.find(".tens").animate({
            top: tens * -lineHeight
        }, animationOptions);

        if (reviewsLeftCount === 0) {
            if (oldCount > 0) {
                // Review just finished, light a champagne supernova in the sky
                Review.highlightDone();
            } else {
                reviewTitleElem
                    .addClass("review-done post-animation")
                    .find("h1")
                    .html(Review.REVIEW_DONE_HTML);
            }
        } else if (!reviewTitleElem.hasClass("review-done")) {
            $("#review-mode-title h1").text(
                reviewsLeftCount === 1 ? "Exercise Left!" : "Exercises Left");
        }

        reviewCounterElem.data("counter", reviewsLeftCount);
    }
};

// Update the "reviewing X exercises" heading counter and also change the
// heading to indicate reviews are done when appropriate
$(function() { APIActionResults.register("reviews_left", Review.updateCounter); });
