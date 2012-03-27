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

// When the user clicks the "Donate" button, get the proper values in
// line to send to PayPal depending on what options are checked.
$("#donation-submit").click(function() {
    var rbval = $('input:radio[name=t3]:checked').val();
    if ( rbval == "O")
    {
        $('#paypal-cmd').val("_donations");
        $('#paypal-item-name').val("One-time donation to Khan Academy");
    }
    else
    {
        $('#paypal-cmd').val("_xclick-subscriptions");
        $('#paypal-item-name').val("Recurring donation to Khan Academy");
        $('#paypal-recurring-amount').val($('#donate-amount').val());
        if ( rbval == "M") {
            $('input[name=srt]').val($('#months-repeating').val())
        } else {
            $('input[name=srt]').val($('#years-repeating').val())
        }

    }
    // Google analytics to track people's clicking the button
    // that takes them to PayPal to make a donation.
    _gaq.push(['_trackEvent', 'Click', 'Donate-Link-Paypal']);

    // Trigger result for donate button test -- did the user click
    // the button to go to PayPal?
    gae_bingo.bingo( "paypal" );
});

// Initialize the accordion behavior.
$(document).ready(function() {
    $("#accordion").accordion({ autoHeight: false, collapsible: true, active: false });
});