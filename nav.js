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

// Simple search through declarations by name, file name and description comment as printed from mathlib directly
// -------------------------

const searchForm = document.getElementById('search_form');
const searchQuery = searchForm.querySelector('input[name=query]');
const searchResults = document.getElementById('search_results');
const maxCountResults = 150;

searchQuery.addEventListener('keydown', (ev) => {
  if (!searchQuery.value || searchQuery.value.length === 0) {
    searchResults.innerHTML = '';
  } else {
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
    }
  }
  
});

searchResults.addEventListener('keydown', (ev) => {
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

function handleSearchCursorUpDown(isDownwards) {
  const selectedResult = document.querySelector(`#${resultsElmntId} .selected`);

  if (selectedResult) {
    selectedResult.classList.remove('selected');
    selectedResult = isDownwards ? selectedResult.nextSibling : selectedResult.previousSibling;
  } else {
    selectedResult = isDownwards ? resultsContainer.firstChild : resultsContainer.lastChild;
  }

  selectedResult && selectedResult.classList.add('selected');
}

function handleSearchItemSelected() {
  // todo goto link made up of the siteRood+module+name
  const selectedResult = document.querySelector(`#${resultsElmntId} .selected`)
  selectedResult.click();
}

// Searching through the index with a specific query and filters
const searchWorkerURL = new URL(`${siteRoot}searchWorker.js`, window.location);
const worker = new SharedWorker(searchWorkerURL);
const searchIndexedData = (query) => new Promise((resolve, reject) => {
  // todo remove when UI filters done
  const filters = {
    attributes: ['nolint'],
    // kind: ['def']
  };

  worker.port.start();
  worker.port.onmessage = ({ data }) => resolve(data);
  worker.port.onmessageerror = (e) => reject(e);
  worker.port.postMessage({ query, maxCount: maxCountResults, filters });
});

const submitSearchFormHandler = async (ev) => {
  ev.preventDefault();
  const query = searchQuery.value;

  if (!query && query.length <= 0) {
    // todo not needed?
    return;
  }

  searchResults.setAttribute('state', 'loading');
  await fillInSearchResultsContainer(query);
  searchResults.setAttribute('state', 'done');
};
searchForm.addEventListener('submit', submitSearchFormHandler);

const fillInSearchResultsContainer = async (query) => {
  const results = await searchIndexedData(query);
  results.sort((a, b) => (a && typeof a.score === "number" && b && typeof b.score === "number") ? (b.score - a.score) : 0);
  searchResults.innerHTML = results.length < 1 ? createNoResultsHTML() : createResultsHTML(results);
}

const createNoResultsHTML = () => '<p class="no_search_result"> No declarations or comments match your search. </p>';

const createResultsHTML = (results) => {
  let html = `<p>Found ${results.length} matches, showing ${maxCountResults > results.length ? results.length : maxCountResults}.</p>`;
  html += results.map((result, index) => {
    return createSingleResultHTML(result, index);
  }).join('');
  return html;
}

const createSingleResultHTML = (result, i) => {
  const { module, name, description, match, terms } = result;
  const resultUrl = `${siteRoot}${module}#${name}`;
  const descriptionDisplay = description && description.length > 0 ? `${description.slice(0, 150)}..` : ''
  
  const html = `<div id="search_result_${i}" class="search_result_item">
    <a href="${resultUrl}" class="search_result_anchor">
      <b class="result_name">${name}</b>
      <br>
      <p class="result_module">${module}</p>
      <p class="result_comment">${descriptionDisplay}</p>
    </a>
  </div>`;

	return html;
} 

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
  searchIndexedData(query).then((results) => {
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






// Rewrite GitHub links
// --------------------

for (const elem of document.getElementsByClassName('gh_link')) {
  const a = elem.firstElementChild;
  // commit is set in add_commit.js
  for (const [prefix, replacement] of commit) {
    if (a.href.startsWith(prefix)) {
      a.href = a.href.replace(prefix, replacement);
      break;
    }
  }
}
