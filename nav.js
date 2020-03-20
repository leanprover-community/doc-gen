var expanded = [];

function unexpand(name) {
    expanded = expanded.filter(function(e) {return e != name;});
    sessionStorage.setItem('expanded', expanded.join(','));
}

function getExpandedCookie() {
    var v = sessionStorage.getItem("expanded");
    if (v) {
        expanded = v.split(',').filter(function(e){return e != "";});
    } else {
        expanded = [];
    }
}

function showItem(item) {
    item.className = "nav_sect_inner";
    expanded.push(item.id);
    sessionStorage.setItem("expanded", expanded.join(","));
}

function hideItem(item) {
    //item.style.display = "none";
    item.className = "nav_sect_inner hidden";
    unexpand(item.id);
}

function expandExpanded() {
    for (var i = 0; i < expanded.length; i++) {
        document.getElementById(expanded[i]).className = "nav_sect_inner";
    }
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
        var content = this.nextElementSibling;
        if (content.className === "nav_sect_inner") {
            hideItem(content);
        } else {
            showItem(content);
        }
    });
}

getExpandedCookie();
expandExpanded();

for (const impl_collapsed of document.getElementsByClassName('impl_collapsed')) {
    const impl_args = impl_collapsed.getElementsByClassName('impl_arg');
    if (impl_args.length > 0) {
        impl_args[0].addEventListener('click', () =>
            impl_collapsed.classList.remove('impl_collapsed'));
    }
}



function filterSelectionClass(tagNames, classname) {
    if (tagNames.length == 0) {
      for (const elem of document.getElementsByClassName(classname)) {
        elem.classList.remove("hide");
      }
    } else {
      // Add the "show" class (display:block) to the filtered elements, and remove the "show" class from the elements that are not selected
      for (const elem of document.getElementsByClassName(classname)) {
        elem.classList.add("hide");
        for (const tagName of tagNames) { 
            if (elem.classList.contains(tagName)) {
              elem.classList.remove("hide");
            }
        }
      }
    }
  }

  function filterSelection(c) {
    filterSelectionClass(c, "tactic");
    filterSelectionClass(c, "taclink");
  }

var filterBoxes = document.getElementsByClassName("tagfilter");

function updateDisplay() {
    //alert(getSelectValues(select));
    filterSelection(getSelectValues());
}

function getSelectValues() {
    var result = [];
  
    for (const opt of filterBoxes) {
  
      if (opt.checked) {
        result.push(opt.value);
      }
    }
    return result;
  }

function setSelectVal(val) {
  for (const opt of filterBoxes) {
    opt.checked = val;
  }
}

updateDisplay();

for (const opt of filterBoxes) {
  opt.addEventListener('change', updateDisplay);
}

document.getElementById("tagfilter-selectall").addEventListener('change', function() {
  setSelectVal(this.checked);
  updateDisplay();
});

//select.addEventListener("click", function() { updateDisplay(); });

//select_input.addEventListener("click", function(event) { updateDisplay(); }, false);
// select.addEventListener("mouseover", function() { updateDisplay(); });