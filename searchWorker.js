const req = new XMLHttpRequest();
req.open('GET', 'decl.txt', false /* blocking */);
req.responseType = 'text';
req.send();

const declNames = req.responseText.split('\n');

importScripts('https://cdn.jsdelivr.net/npm/minisearch@2.4.1/dist/umd/index.min.js');
const miniSearch = new MiniSearch({
    fields: ['decl'],
    storeFields: ['decl'],
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