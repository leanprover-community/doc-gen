var obj = JSON.parse(json_str);
var urlParams = new URLSearchParams(window.location.search);
var declName = urlParams.get('decl')
window.location.replace(obj[declName] + '#' + declName);