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
  currentFileLink.scrollIntoView({block: 'center'});
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

const declURL = new URL(`${siteRoot}searchable_data.bmp`, window.location);
const getDecls = (() => {
  let decls;
  return () => {
    if (!decls) decls = new Promise((resolve, reject) => {
        const req = new XMLHttpRequest();
        req.responseType = 'json';
        req.addEventListener('load', () => resolve(loadDecls(req.response)));
        req.addEventListener('error', () => reject());
        req.open('GET', declURL);
        req.send();
      })
    return decls;
  }
})()

const declSearch = async (q) => getMatches(await getDecls(), q);

const srId = 'search_results';
document.getElementById('search_form')
  .appendChild(document.createElement('div'))
  .id = srId;

function handleSearchCursorUpDown(down) {
  const sel = document.querySelector(`#${srId} .selected`);
  const sr = document.getElementById(srId);
  if (sel) {
    sel.classList.remove('selected');
    const toSelect = down ?
      sel.nextSibling || sr.firstChild:
      sel.previousSibling || sr.lastChild;
    toSelect && toSelect.classList.add('selected');
  } else {
    const toSelect = down ? sr.firstChild : sr.lastChild;
    toSelect && toSelect.classList.add('selected');
  }
}

function handleSearchEnter() {
  const sel = document.querySelector(`#${srId} .selected`)
    || document.getElementById(srId).firstChild;
  sel.click();
}

const searchInput = document.querySelector('#search_form input[name=q]');

searchInput.addEventListener('keydown', (ev) => {
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
      handleSearchEnter();
      break;
  }
});

searchInput.addEventListener('input', async (ev) => {
  const text = ev.target.value;

  if (!text) {
    const sr = document.getElementById(srId);
    sr.removeAttribute('state');
    sr.replaceWith(sr.cloneNode(false));
    return;
  }

  document.getElementById(srId).setAttribute('state', 'loading');

  const result = await declSearch(text);
  if (ev.target.value != text) return;

  const oldSR = document.getElementById('search_results');
  const sr = oldSR.cloneNode(false);
  for (const {decl} of result) {
    const d = sr.appendChild(document.createElement('a'));
    d.innerText = decl;
    d.title = decl;
    d.href = `${siteRoot}find/${decl}`;
  }
  sr.setAttribute('state', 'done');
  oldSR.replaceWith(sr);
});






// 404 page goodies
// ----------------

const howabout = document.getElementById('howabout');
if (howabout) {
  howabout.innerText = "Please wait a second.  I'll try to help you.";

  howabout.parentNode
      .insertBefore(document.createElement('pre'), howabout)
      .appendChild(document.createElement('code'))
      .innerText = window.location.href.replace(/[/]/g, '/\u200b');

  const query = window.location.href.match(/[/]([^/]+)(?:\.html|[/])?$/)[1];
  declSearch(query).then((results) => {
      howabout.innerText = 'How about one of these instead:';
      const ul = howabout.appendChild(document.createElement('ul'));
      for (const {decl} of results) {
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

// Informal Statement feedback form handler
// -------

/** Same as `fetch` but throws an error if it's a bad response. */
async function fetchGood(...args) {
  const response = await fetch(...args);
  if (!response.ok)  {
    const txt = await response.text()
    throw new Error(`Bad response: ${txt}`)
  }
}

/** Handler for clicking feedback buttons in informal statements. */
window.addEventListener('load', _ => {
  for (const translationDiv of document.querySelectorAll('.translation_qs')) {
    const declName = translationDiv.getAttribute('data-decl')
    if (!declName) {
      console.error('no data-decl on translation_qs')
    }
    const feedbackForm = translationDiv.querySelector('.informal_statement_feedback')
    const editForm = translationDiv.querySelector('.informal_statement_edit')
    const ta = editForm.querySelector('textarea')
    const url = new URL(feedbackForm.getAttribute('action'));
    url.searchParams.set('decl', declName)
    url.searchParams.set('statement', ta.value)
    feedbackForm.addEventListener('submit', async event => {
      event.preventDefault()
      try {
        const value = event.submitter.getAttribute('value')
        url.searchParams.set('rate', value)
        feedbackForm.textContent = "Sending..."
        await fetchGood(url, { method: 'POST' });
        if (value === 'no') {
          feedbackForm.textContent = "Thanks for your feedback! Optionally, please help us out by submitting a corrected statement: "
          editForm.removeAttribute('style')
          const edit = await new Promise((resolve, reject) => {
            editForm.addEventListener('submit', event => {
              event.preventDefault()
              resolve(ta.value)
            })
          });
          url.searchParams.delete('rate') // don't double-count the rating.
          url.searchParams.set('edit', edit)
          editForm.remove()
          feedbackForm.textContent = "Sending...";
          await fetchGood(url, { method: 'POST' });
        }
        feedbackForm.textContent = "Thanks for your feedback!"
      } catch (err) {
        feedbackForm.textContent = `Error: ${err.message}`
      }
    })
  }
})

const INFORMAL_OPEN_ID = 'informal_statement_open';
function updateInformalOpen(state) {
  if (state !== undefined) {
    localStorage.setItem(INFORMAL_OPEN_ID, state);
  } else {
    state = localStorage.getItem(INFORMAL_OPEN_ID) ?? true;
  }
  const details = document.querySelectorAll('.informal_statement_details');
  for (const detail of details) {
    if (state) {
      detail.setAttribute('open', '');
    } else {
      detail.removeAttribute('open');
    }
  }
}

window.addEventListener('load', _ => {
  updateInformalOpen();
  const checkbox = document.querySelector('#informal-open');
  checkbox.checked = localStorage.getItem(INFORMAL_OPEN_ID) ?? true
  checkbox.addEventListener('change', e => {
    const value = checkbox.checked
    updateInformalOpen(value)
  })
})