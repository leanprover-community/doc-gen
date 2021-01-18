const req = new XMLHttpRequest();
req.open('GET', 'decl.txt', false /* blocking */);
req.responseType = 'text';
req.send();

const declNames = req.responseText.split('\n');

// Adapted from the default tokenizer and
// https://util.unicode.org/UnicodeJsps/list-unicodeset.jsp?a=%5Cp%7BZ%7D&abb=on&c=on&esc=on&g=&i=
const SEPARATOR = /[._\n\r \u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]+/u

importScripts('https://cdn.jsdelivr.net/npm/minisearch@2.4.1/dist/umd/index.min.js');
const miniSearch = new MiniSearch({
    fields: ['decl'],
    storeFields: ['decl'],
    tokenize: text => text.split(SEPARATOR),
});
miniSearch.addAll(declNames.map((decl, id) => ({decl, id})));

onconnect = ({ports: [port]}) =>
    port.onmessage = ({data}) => {
        const results = miniSearch.search(data.q, {
            prefix: (term) => term.length > 3,
            fuzzy: (term) => term.length > 3 && 0.2,
        });
        port.postMessage(results.slice(0, 20));
    };
