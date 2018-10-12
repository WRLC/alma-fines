// login urls
function submitLogin() {
    var sp = "https://aladin-sp.wrlc.org/simplesaml/wrlcauth/issue.php?institution="
    var params = "&url=https://fines.wrlc.org/login/n"
    var select = document.getElementById('user-name');
    var institution = select.options[select.selectedIndex].value;
    window.location.replace(sp + institution + params);
    return false;
}
