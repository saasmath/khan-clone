// When the user clicks a donate radio button, display or hide the recurring frequency
// section and shift it based on.
//
// Some tomfoolery going on here, using a combination of visibility and display to make
// thisgs show up properly.
$('input[name=t3]:radio').click(function() {
    var paypal_cmd = $('#paypal-cmd');
    var rbval = $('input:radio[name=t3]:checked').val();
    if (rbval == "O")
    {
        $('#recurring-frequency-months').css("visibility", "hidden");
        $('#recurring-frequency-months').css("display", "inline");
        $('#recurring-frequency-years').css("display", "none");
    } else if (rbval == "M") {
        $('#recurring-frequency-months').css("visibility", "visible");
        $('#recurring-frequency-months').css("display", "inline");
        $('#recurring-frequency-years').css("display", "none");
    } else {
        $('#recurring-frequency-months').css("display", "none");
        $('#recurring-frequency-years').css("display", "inline");                   
    }
});

// Called to trigger the show/hide behavior when the page is loaded or reloaded.
// Otherwise, the field may not be displayed properly.
$('input:radio[name=t3]:checked').click();

var submitPaypal = function() {
    $('#paypal-form').submit();
};

// When the user clicks the "Donate" button, get the proper values in
// line to send to PayPal depending on what options are checked.
$("#donation-submit").click(function(e) {
    // Disable the form's default submit action because we do it
    // as a callback from bingo.
    e.preventDefault();
    var rbval = $('input:radio[name=t3]:checked').val();
    var amount = $('#donate-amount').val();
    var duration = "One-Time";

    if ( rbval === "O")
    {
        $('#paypal-cmd').val("_donations");
        $('#paypal-item-name').val("One-time donation to Khan Academy");
    }
    else
    {
        $('#paypal-cmd').val("_xclick-subscriptions");
        $('#paypal-item-name').val("Recurring donation to Khan Academy");
        $('#paypal-recurring-amount').val(amount);
        var period = (rbval === "M" ? $('#months-repeating').val() : $('#years-repeating').val());

        // Create a string for the duration to report to MixPanel.
        duration = (period !== "0" ? period : "ongoing") + " " + (rbval === "M" ? "months" : "years");
        $('input[name=srt]').val(period);
    }
    // mixpanel.com to track people's clicking the button
    // that takes them to PayPal to make a donation.
    Analytics.trackSingleEvent("Donate-Link-Paypal",
                                {"Amount": amount,
                                 "Duration": duration});
    // NOTE: When this bingo is turned off, we'll need to reactivate
    // the form's submit action.
    gae_bingo.bingo( "hp_donate_button_paypal", submitPaypal, submitPaypal);
});

// Initialize the accordion behavior.
$(document).ready(function() {
    $("#accordion").accordion({ autoHeight: false, collapsible: true, active: false });
});