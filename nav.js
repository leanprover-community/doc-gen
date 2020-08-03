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

function memo(thunk) {
  let val = null;
  return () => val || (val = thunk());
}

const loadDeclTxt = memo(() => new Promise((resolve, reject) => {
  const req = new XMLHttpRequest();
  req.onload = () => resolve(req.responseText.split('\n'));
  req.onerror = req.onabort = () => reject('failed to load file');
  req.open('GET', siteRoot + 'decl.txt');
  req.responseType = 'text';
  req.send();
}));

const mkDeclIndex = memo(async () => {
  const docs = (await loadDeclTxt()).map((decl, id) => ({decl, id}));
  const miniSearch = new MiniSearch({
    fields: ['decl'],
    storeFields: ['decl'],
  });
  await miniSearch.addAllAsync(docs);
  return miniSearch;
});
const declsMatching = async (pat) =>
  (await mkDeclIndex()).search(pat, {
      prefix: (term) => term.length > 3,
      fuzzy: (term) => term.length > 3 && 0.2,
    });

const headerSearchInput = document.querySelector('.header_search input[name=q]');

headerSearchInput.addEventListener('input', async (ev) => {
  const text = ev.target.value;

  // Super hack: there's no way to know whether a user selected a suggestion, so
  // we append a zero-width space to the suggestion.
  if (text.endsWith('\u200b')) {
    window.location.href = `${siteRoot}find/` + text.slice(0, -1);
    return;
  }

  const decls = await declsMatching(text);
  if (ev.target.value != text) return;

  const oldDatalist = document.querySelector('datalist#search_suggestions');
  const datalist = oldDatalist.cloneNode(false);
  for (const {decl} of decls.slice(0, 10)) {
    const option = document.createElement('option');
    option.value = decl + '\u200b';
    datalist.appendChild(option);
  }
  oldDatalist.replaceWith(datalist);
});