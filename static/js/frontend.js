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
    });
});

// search users warning
$(function(){
    $("#lookup-user").on("submit", function(){
        $("#lookup-form-div").after(
            //'<div class="spinner-grow" role="status"><span class="sr-only">Loading...</span></div>'
            `<div class="spinner-grow" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            <div id="loading-message" class="d-inline-block p-2">
                <span id="loading-message" class="font-weight-bold">Searching for fines accross all WRLC IZss. This takes a moment...</span>
            </div>`
        );
    });
});
