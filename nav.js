// Persistent expansion cookie for the file tree
// ---------------------------------------------

let expanded = {};
for (const e of (sessionStorage.getItem('expanded') || '').split(',')) {
  if (e !== '') {
    expanded[e] = true;
  }
}

function saveExpanded() {
  sessionStorage.setItem("expanded",
    Object.getOwnPropertyNames(expanded).filter((e) => expanded[e]).join(","));
}

for (const elem of document.getElementsByClassName('nav_sect')) {
  const id = elem.getAttribute('data-path');
  if (!id) continue;
  if (expanded[id]) {
    elem.open = true;
  }
  elem.addEventListener('toggle', () => {
    expanded[id] = elem.open;
    saveExpanded();
  });
}

for (const currentFileLink of document.getElementsByClassName('visible')) {
  setTimeout(() => currentFileLink.scrollIntoView(), 0);
}






// Expansion of implicit arguments ({...})
// ---------------------------------------


for (const impl_collapsed of document.getElementsByClassName('impl_collapsed')) {
    const impl_args = impl_collapsed.getElementsByClassName('impl_arg');
    if (impl_args.length > 0) {
        impl_args[0].addEventListener('click', () =>
            impl_collapsed.classList.remove('impl_collapsed'));
    }
}







// Tactic list tag filter
// ----------------------

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

const tse = document.getElementById("tagfilter-selectall")
if (tse != null) {
  tse.addEventListener('change', function() {
    setSelectVal(this.checked);
    updateDisplay();
  });
}




// Simple declaration search
// -------------------------

const searchWorkerURL = new URL(`${siteRoot}searchWorker.js`, window.location);
const declSearch = (q) => new Promise((resolve, reject) => {
  const worker = new SharedWorker(searchWorkerURL);
  worker.port.start();
  worker.port.onmessage = ({data}) => resolve(data);
  worker.port.onmessageerror = (e) => reject(e);
  worker.port.postMessage({q});
});

document.querySelector('.header_search input[name=q]').addEventListener('input', async (ev) => {
  const text = ev.target.value;

  // Super hack: there's no way to know whether a user selected a suggestion, so
  // we append a zero-width space to the suggestion.
  if (text.endsWith('\u200b')) {
    window.location.href = `${siteRoot}find/` + text.slice(0, -1);
    return;
  }

  const result = await declSearch(text);
  if (ev.target.value != text) return;

  const oldDatalist = document.querySelector('datalist#search_suggestions');
  const datalist = oldDatalist.cloneNode(false);
  for (const {decl} of result) {
    const option = document.createElement('option');
    option.value = decl + '\u200b';
    datalist.appendChild(option);
  }
  oldDatalist.replaceWith(datalist);
});