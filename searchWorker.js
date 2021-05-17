// Access indexed data structure to be used for searching through the documentation
const req = new XMLHttpRequest();

req.open('GET', 'searchable_data.json', false /* blocking */);
req.responseType = 'json';
req.send();

importScripts('https://cdn.jsdelivr.net/npm/minisearch@2.4.1/dist/umd/index.min.js');
    // Include options as per API specs: https://lucaong.github.io/minisearch/modules/_minisearch_.html
const miniSearch = new MiniSearch({
    idField: 'name',
    fields: ['module', 'name', 'description'],
    storeFields: ['module', 'name', 'description', 'attributes', 'kind']
});

const indexedData = req.response;
miniSearch.addAll(indexedData);

onconnect = ({ports: [port]}) =>
port.onmessage = ({ data }) => {
    const { query, filters, maxCount } = data;
    const filterFunc = (result) => filterItemResult(result, filters);
    const sanitizedQuery = query.trim();
    if (sanitizedQuery && typeof sanitizedQuery === "string" && sanitizedQuery.length > 0) {
        const results = miniSearch.search(sanitizedQuery, {
            boost: { module: 1, description: 2, name: 3 },
            combineWith: 'AND',
            filter: filterFunc,
            // prefix: (term) => term.length > 3,
            // fuzzy: (term) => term.length > 3 && 0.2,
        });
        
        const response = typeof maxCount === "number" && maxCount >= 0 ? results.slice(0, maxCount) : results;
        console.log(response)
        port.postMessage({response, total: results.length});
    }
    port.postMessage({response: [], total: 0});
};

const filterItemResult = (result, filters = {}) => {
    const { attributes: attrFilter, kind: kindFilter } = filters;
    const hasAttrFilter = attrFilter && attrFilter.length > 0;
    const hasKindFilter = kindFilter && kindFilter.length > 0;

    if (!hasAttrFilter && !hasKindFilter) {
        return true;
    }
    
    const { attributes: attrRes, kind: kindRes } = result;
    let isResultAttrIncluded = false;
    let isResultKindIncluded = false;

    if (hasKindFilter) {
        isResultKindIncluded = kindFilter.includes(kindRes);
    }

    if (hasAttrFilter) {
        for (let attribute of attrRes) {
            if (attrFilter.includes(attribute)) {
                isResultAttrIncluded = true;
                break;
            }
        }
    } 

    return hasKindFilter && hasAttrFilter ? 
        (isResultAttrIncluded && isResultKindIncluded) : 
        hasAttrFilter ? 
            isResultAttrIncluded : 
            isResultKindIncluded;
}