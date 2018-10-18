// frontend js functions

// login form
function submitLogin() {
    var sp = "https://aladin-sp.wrlc.org/simplesaml/wrlcauth/issue.php?institution="
    var params = "&url=https://fines.wrlc.org/login/n"
    var select = document.getElementById('user-name');
    var institution = select.options[select.selectedIndex].value;
    window.location.replace(sp + institution + params);
    return false;
}

function validatePayments() {
    $("#fines").children("table").each(function(){
        var tid = $(this).attr("id");
        $("#fee-list-" + tid).children("tr").each(function(){
            //console.log($(this).children("td").text())
            var balance = $(this).children("td").find("[type=checkbox]").attr("data-fine-balance");
            var paymentAmount = $(this).children("td").find("[type=text]").val();
            // need to convert from txt to ints (*100 or whatever)
            if (paymentAmount > balance) {
                return false
            } else if (paymentAmount <= 0) {
                return false
            }

        })
    return true
    });
}

// payment form
$(function(){
    $("#fines").on("submit", function(){
    //$("#fines").on("submit", function(e){
        var finesSelected = new Object();
        $("#fines input:checked").each(function() {
            var fineLink = $(this).attr('value');
            var fineInst = $(this).attr('data-fine-inst');
            var fineAmount = $(this).attr('data-fine-balance');
            
            finesSelected[fineInst] = finesSelected[fineInst] || [];
            finesSelected[fineInst].push({'link':fineLink,
					  'amount':fineAmount});
        });
        $("#payments").attr('value', JSON.stringify(finesSelected));
        //e.preventDefault();
	if ( validatePayments() ){
        alert("VALID");
        return false;
    } else {
	    alert("NOT VALID");
	    return false;
	}
    });
});
