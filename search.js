function isSep(c) {
    return c === '.' || c === '_';
}

function matchCaseSensitive(declName, lowerDeclName, pat) {
    let i = 0, j = 0, err = 0, lastMatch = 0
    while (i < declName.length && j < pat.length) {
        if (pat[j] === declName[i] || pat[j] === lowerDeclName[i]) {
            err += (isSep(pat[j]) ? 0.125 : 1) * (i - lastMatch);
            if (pat[j] !== declName[i]) err += 0.5;
            lastMatch = i + 1;
            j++;
        } else if (isSep(declName[i])) {
            err += 0.125 * (i + 1 - lastMatch);
            lastMatch = i + 1;
        }
        i++;
    }
    err += 0.125 * (declName.length - lastMatch);
    if (j === pat.length) {
        return err;
    }
}

function loadDecls(declBmpCnt) {
    return declBmpCnt.split('\n').map(d => [d, d.toLowerCase()]);
}

function getMatches(decls, pat, maxResults = 20) {
    // const lowerPat = pat.toLowerCase();
    // const caseSensitive = pat !== lowerPat;
    const results = [];
    for (const [decl, lowerDecl] of decls) {
        const err = matchCaseSensitive(decl, lowerDecl, pat);
        if (err !== undefined) {
            results.push({decl, err});
        }
    }
    return results.sort(({err: a}, {err: b}) => a - b).slice(0, maxResults);
}

if (typeof process === 'object') { // NodeJS
    const declNames = loadDecls(require('fs').readFileSync('html/decl.bmp').toString());
    console.log(getMatches(declNames, process.argv[2] || 'ltltle', 20));
}