// adapted from https://www.tutorialspoint.com/levenshtein-distance-in-javascript
function editDistance(str1, str2) {
    const matrix = Array(str2.length + 1).fill(null).map(
        () => Array(str1.length + 1).fill(null)
    );
    for (let i = 0; i <= str1.length; i += 1) {
        matrix[0][i] = i;
    }
    for (let j = 0; j <= str2.length; j += 1) {
        matrix[j][0] = j;
    }
    for (let j = 1; j <= str2.length; j += 1) {
        for (let i = 1; i <= str1.length; i += 1) {
            const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
            matrix[j][i] = Math.min(
                matrix[j][i - 1] + 1, // deletion
                matrix[j - 1][i] + 1, // insertion
                matrix[j - 1][i - 1] + indicator, // substitution
            );
        }
    }
    return matrix[str2.length][str1.length];
}

function splitDecls(declBmpCnt) {
    return declBmpCnt.trim().split('\n');
}

function getMatches(decls, patt, maxResults = 20) {
    const results = [];
    for (const decl of decls) {
        const dist = editDistance(decl.toLowerCase(), patt.toLowerCase());
        results.push({decl, dist});
    }
    return results.sort(({dist: a}, {dist: b}) => a - b).slice(0, maxResults);
}

if (typeof process === 'object') { // NodeJS
    const declNames = splitDecls(require('fs').readFileSync('html/decl.bmp').toString());
    console.log(getMatches(declNames, process.argv[2] || 'ltltle', 20));
}
