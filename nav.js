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

// Simple search through declarations by name, file name and description comment as printed from mathlib
// -------------------------
const MAX_COUNT_RESULTS = 10;

/* Get all elements for searching and showing results */
const searchForm = document.getElementById('search_form');
const searchQueryInput = searchForm.querySelector('input[name=query]');
const searchResultsContainer = document.getElementById('search_results');

/* Handle opening/closing search results container */
function closeResultsDisplay() {
  searchResultsContainer.style.display = 'none';
}

function openResultsDisplay() {
  searchResultsContainer.style.display = 'block';
}

/* Handle resizing search results container */
const SMALL = 'condensed';
const LARGE = 'full_width';
function renderSmallResultsContainer() {
  searchResultsContainer.classList.contains(LARGE) 
  ? 
    searchResultsContainer.classList.contains(SMALL) 
    ?
      searchResultsContainer.classList.remove(LARGE) 
    :
      searchResultsContainer.classList.replace(LARGE, SMALL) 
  : 
    !searchResultsContainer.classList.contains(SMALL) && searchResultsContainer.classList.add(SMALL);
}

function renderLargeResultsContainer() {
  searchResultsContainer.classList.contains(SMALL) 
  ? 
    searchResultsContainer.classList.contains(LARGE) 
    ?
      searchResultsContainer.classList.remove(SMALL) 
    :
      searchResultsContainer.classList.replace(SMALL, LARGE) 
  : 
    !searchResultsContainer.classList.contains(LARGE) && searchResultsContainer.classList.add(LARGE);
}
/* Set up defaults for search filtering and results */ 
const filters = {
  attributes: [],
  kind: []
};

/* Handle searching through the index with a specific query and filters */
const searchWorkerURL = new URL(`${siteRoot}searchWorker.js`, window.location);
const worker = new SharedWorker(searchWorkerURL);
const searchIndexedData = (query, maxResultsCount) => new Promise((resolve, reject) => {
  const maxCount = typeof maxResultsCount === "number" ? maxResultsCount : MAX_COUNT_RESULTS;

  worker.port.start();
  worker.port.onmessage = ({ data }) => resolve(data);
  worker.port.onmessageerror = (e) => reject(e);
  worker.port.postMessage({ query, maxCount, filters });
});

/* Submitting search query */
const submitSearchFormHandler = async (ev) => {
  ev?.preventDefault();
  closeFiltersDisplay();
  
  const query = searchQueryInput.value;
  if (!query || query.length <= 0) {
    closeResultsDisplay();
    return;
  }
  renderSmallResultsContainer();
  openResultsDisplay();


  searchResultsContainer.setAttribute('state', 'loading');
  await fillInSearchResultsContainer(query);
  searchResultsContainer.setAttribute('state', 'done');

  const searchResultsContainerCloseBtn = document.getElementById('close_results_btn');
  searchResultsContainerCloseBtn?.addEventListener("click", closeResultsDisplay);

  const searchResultsShowAllBtn = document.getElementById('show_all_results_btn');
  searchResultsShowAllBtn?.addEventListener('click', () => renderAllResultsHtml(query));
};
searchForm.addEventListener('submit', submitSearchFormHandler);

const renderAllResultsHtml = async (query) => {
  if (!query && query.length <= 0) {
    closeResultsDisplay();
    return;
  }

  searchResultsContainer.setAttribute('state', 'loading');
  await fillInSearchResultsContainer(query, true);
  
  renderLargeResultsContainer();
  openResultsDisplay();
  searchResultsContainer.setAttribute('state', 'done');

  const searchResultsContainerCloseBtn = document.getElementById('close_results_btn');
  searchResultsContainerCloseBtn?.addEventListener("click", closeResultsDisplay);
}

const fillInSearchResultsContainer = async (query, showAll = false) => {
  searchResultsContainer.innerHTML = '';
  const resultsCount = showAll ? -1 : MAX_COUNT_RESULTS;
  const {response: results, total} = await searchIndexedData(query, resultsCount);
  results.sort((a, b) => (a && typeof a.score === "number" && b && typeof b.score === "number") ? (b.score - a.score) : 0);

  const searchResultsCloseBtn = '<span class="close" id="close_results_btn">x</span>';
  searchResultsContainer.innerHTML = results.length < 1 ? createNoResultsHTML(searchResultsCloseBtn) : createResultsHTML(results, total, showAll, searchResultsCloseBtn);
}

const createNoResultsHTML = (html) => `<p class="no_search_result"> No declarations or comments match your search. </p>${html}`;

const createResultsHTML = (results, total, showAll, html) => {
  const descriptionMaxLength = showAll ? 350 : 80;
  const countShowingResults = MAX_COUNT_RESULTS > results.length ? results.length : MAX_COUNT_RESULTS;

  let resultHtml = `<p id="search_info">Found ${total} matches 
    ${!showAll ?
      `, showing ${countShowingResults}.</p><span id="show_all_results_btn" class="link_coloring">Show all</span>` :
      ''
    }
  ${html}`;
  resultHtml += results.map((result, index) => {
    return createSingleResultHTML(result, descriptionMaxLength, index);
  }).join('');
  return resultHtml;
}

const createSingleResultHTML = (result, descriptionMaxLength, i) => {
  const { module, name, description } = result;
  const resultUrl = `${siteRoot}${module}#${name}`;
  const descriptionDisplay = description && description.length > 0 ? 
    `${description.slice(0, descriptionMaxLength)}${description.length > descriptionMaxLength ? '..' : ''}` :
    '';

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

/* Keyboard navigation through search input and results */
searchQueryInput.addEventListener('keydown', (ev) => {
  if (!searchQueryInput.value || searchQueryInput.value.length === 0) {
    searchResultsContainer.innerHTML = '';
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

searchResultsContainer.addEventListener('keydown', (ev) => {
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
  const selectedResult = document.querySelector(`#${resultsElmntId} .selected`)
  selectedResult.click();
}



// Simple filtering by *attributes* and *kind* per declaration
// -------------------------

/* Get all elements for filtering */
const filtersToggleButton = document.getElementById('search_filters_btn');
const filtersContainer = document.getElementById('filters_container');
const filtersForm = document.getElementById('filters_form');
const closeFiltersBtn = document.getElementById('close_filters_btn');

/* Handle opening/closing filters container */
function closeFiltersDisplay() {
  filtersContainer.style.display = 'none';
}
closeFiltersBtn.addEventListener("click", closeFiltersDisplay);

function openFiltersDisplay() {
  filtersContainer.style.display = 'block';
}

function toggleFiltersDisplay() {
  const filtersContainerStyle = (!filtersContainer.style.display || filtersContainer.style.display.length === 0) ?
    getComputedStyle(filtersContainer).display : 
    filtersContainer.style.display;
  const isOpen = filtersContainerStyle !== 'none';
  if (isOpen) {
    closeFiltersDisplay();
  } else {
    openFiltersDisplay();
  }
}
filtersToggleButton.addEventListener("click", toggleFiltersDisplay);

/* Handle submit chosen filters */
const submitFiltersFormHandler = (ev) => {
  ev.preventDefault();
  const attributeBoxNodes = filtersForm.querySelectorAll('input[name=attribute]:checked');
  const kindBoxNodes = filtersForm.querySelectorAll('input[name=kind]:checked');

  
  filters.attributes = [];
  attributeBoxNodes?.forEach(e => filters.attributes.push(e.value));

  filters.kind = [];
  kindBoxNodes?.forEach(e => filters.kind.push(e.value));

  closeFiltersDisplay();
  submitSearchFormHandler(ev);
};
filtersForm.addEventListener('submit', submitFiltersFormHandler);




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
