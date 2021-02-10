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
  currentFileLink.scrollIntoView({ block: 'center' });
}

// Tactic list tag filter
// ---------------------- 

function filterSelectionClass(tagNames, className) {
  if (tagNames.length === 0) {
    for (const elem of document.getElementsByClassName(className)) {
      elem.classList.remove("hide");
    }
  } else {
    // Add the "show" class (display:block) to the filtered elements, and remove the "show" class from the elements that are not selected
    for (const elem of document.getElementsByClassName(className)) {
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

var filterBoxesElmnts = document.getElementsByClassName("tagfilter");

function updateDisplay() {
  filterSelection(getSelectValues());
}

function getSelectValues() {
  var result = [];
  for (const opt of filterBoxesElmnts) {
    if (opt.checked) {
      result.push(opt.value);
    }
  }
  return result;
}

function setSelectVal(val) {
  for (const opt of filterBoxesElmnts) {
    opt.checked = val;
  }
}

updateDisplay();

for (const opt of filterBoxesElmnts) {
  opt.addEventListener('change', updateDisplay);
}

const tse = document.getElementById("tagfilter-selectall");
if (tse !== null) {
  tse.addEventListener('change', function () {
    setSelectVal(this.checked);
    updateDisplay();
  });
}

// Simple search through declarations by name
// -------------------------

const searchWorkerURL = new URL(`${siteRoot}searchWorker.js`, window.location);
const declSearch = (query) => new Promise((resolve, reject) => {
  const worker = new SharedWorker(searchWorkerURL);
  worker.port.start();
  worker.port.onmessage = ({ data }) => resolve(data);
  worker.port.onmessageerror = (e) => reject(e);
  worker.port.postMessage({ query });
});

const resultsElmntId = 'search_results';
document.getElementById('search_form')
  .appendChild(document.createElement('div'))
  .id = resultsElmntId; // todo add on creation of page, not here

function handleSearchCursorUpDown(down) {
  const selectedResult = document.querySelector(`#${resultsElmntId} .selected`);
  const resultsElmnt = document.getElementById(resultsElmntId);

  let toSelect = down ? resultsElmnt.firstChild : resultsElmnt.lastChild;
  if (selectedResult) {
    selectedResult.classList.remove('selected');
    toSelect = down ? selectedResult.nextSibling : selectedResult.previousSibling;
  }
  toSelect && toSelect.classList.add('selected');
}

function handleSearchItemSelected() {
  const selectedResult = document.querySelector(`#${resultsElmntId} .selected`)
  selectedResult.click();
}

const searchInputElmnt = document.querySelector('#search_form input[name=q]');

// todo use Enter to start searching if we still in <input /> and not <div />
searchInputElmnt.addEventListener('keydown', (ev) => {
  switch (ev.key) {
    case 'Down':
    case 'ArrowDown':
      ev.preventDefault();
      handleSearchCursorUpDown(true);
      break;
    case 'Up':
    case 'ArrowUp':
      ev.preventDefault();
      handleSearchCursorUpDown(false);
      break;
    case 'Enter':
      ev.preventDefault();
      handleSearchItemSelected();
      break;
  }
});

searchInputElmnt.addEventListener('input', async (ev) => {
  const text = ev.target.value;

  if (!text) {
    const resultsElmnt = document.getElementById(resultsElmntId);
    resultsElmnt.removeAttribute('state');
    resultsElmnt.replaceWith(resultsElmnt.cloneNode(false));
    return;
  }

  document.getElementById(resultsElmntId).setAttribute('state', 'loading');

  const result = await declSearch(text);
  if (ev.target.value != text) return; // todo why?

  const currentResultsElmnt = document.getElementById('search_results');
  const resultsElmntCopy = currentResultsElmnt.cloneNode(false);
  for (const { decl } of result) {
    const d = resultsElmntCopy.appendChild(document.createElement('a'));
    d.innerText = decl;
    d.title = decl;
    d.href = `${siteRoot}find/${decl}`;
  }
  resultsElmntCopy.setAttribute('state', 'done');
  currentResultsElmnt.replaceWith(resultsElmntCopy);
});

// 404 page goodies
// ----------------

const suggestionsElmnt = document.getElementById('howabout');
if (suggestionsElmnt) {
  suggestionsElmnt.innerText = "Please wait a second.  I'll try to help you.";

  suggestionsElmnt.parentNode
    .insertBefore(document.createElement('pre'), suggestionsElmnt)
    .appendChild(document.createElement('code'))
    .innerText = window.location.href.replace(/[/]/g, '/\u200b');

  const query = window.location.href.match(/[/]([^/]+)(?:\.html|[/])?$/)[1];
  declSearch(query).then((results) => {
    suggestionsElmnt.innerText = 'How about one of these instead:';
    const ul = suggestionsElmnt.appendChild(document.createElement('ul'));
    for (const { decl } of results) {
      const li = ul.appendChild(document.createElement('li'));
      const a = li.appendChild(document.createElement('a'));
      a.href = `${siteRoot}find/${decl}`;
      a.appendChild(document.createElement('code')).innerText = decl;
    }
  });
}
