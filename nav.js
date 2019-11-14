var expanded = [];

function unexpand(name) {
    expanded = expanded.filter(function(e) {return e != name;});
}

function getQueryVariable(variable) {
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    for (var i = 0; i < vars.length; i++) {
        var pair = vars[i].split("=");
        if (pair[0] == variable) { return pair[1]; }
    }
    return (false);
}

function updateContent(path, midPos = 0, rightPos = 0) {
    var content_div = document.getElementById('content');
    $(content_div).load("html/" + path);
    var anchor = document.getElementById("column_middle");
    //anchor.scrollTo(0, midPos);
    var nav_div = document.getElementById('internal_nav');
    $(nav_div).load("html/" + path + ".nav");
    anchor = document.getElementById("column_right");
    //anchor.scrollTo(0, rightPos);
    document.title = "mathlib API docs: " + path;

    var coll = document.getElementsByClassName("nav_file visible");
    for (i = 0; i < coll.length; i++) {
        coll[i].className = "nav_file";
    }
    document.getElementById(path).className = "nav_file visible";
}

function getUrl() {
    return window.location.href.split('?')[0];
}

function showItem(item) {
    item.style.display = "block";
    expanded.push(item.id);
}

function hideItem(item) {
    item.style.display = "none";
    unexpand(item.id);
}

function showNav(path) {
    var items = path.split("/");
    var i;
    for (i = 0; i < items.length - 1; i++) {
        d = document.getElementById(items.slice(0, i + 1).join("/"));
        showItem(d);
    }
}

var coll = document.getElementsByClassName("nav_sect");
var i;
for (i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function () {
        //this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.display === "block") {
            hideItem(content);
        } else {
            showItem(content);
        }
    });
}

function getScrollPos(name) {
    var obj = document.getElementById(name);
    return obj.scrollTop;
}

function setCurrentState() {
    var mid = getScrollPos("column_middle");
    var rig = getScrollPos("column_right");
    window.history.replaceState({"contline":mid, "navline":rig}, "");
}


function setScrollPos(m, r) {
    var obj = document.getElementById("column_middle");
    obj.scrollTop = m;
    obj = document.getElementById("column_right");
    obj.scrollTop = r;
}

function resetScrollPos() {
    setScrollPos(0, 0);
}

var coll = document.getElementsByClassName("nav_file");
for (i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function () {
        //this.classList.toggle("active");
        //setCurrentState();
        updateContent(this.href);
        resetScrollPos()
        //window.history.pushState({"contline":mid, "navline":rig, "msg":"this was added when I clicked on " + this.id}, "", window.location.href);
        //window.location.href = getUrl() + '?page=' + this.id;
        window.history.pushState({"contline":0, "navline":0}, "", getUrl() + '?page=' + this.id);
    });
}

window.onpopstate = function (e) {
    //setCurrentState();
    if (e.state) {
        var page = getQueryVariable("page");
        updateContent(page); // , e.state["contline"], e.state["navline"]);
        setScrollPos(e.state["contline"], e.state["navline"]);
    }
};


q = getQueryVariable("page");
if (q != "") {
    updateContent(q);
    showNav(q);
}

var obj = document.getElementById("column_middle");
obj.addEventListener("scroll", function(ev) {setCurrentState()});
obj = document.getElementById("column_right");
obj.addEventListener("scroll", function(ev) {setCurrentState()});