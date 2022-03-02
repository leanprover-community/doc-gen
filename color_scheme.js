function getTheme() {
    return localStorage.getItem("theme") || "system";
}

function setTheme(themeName) {
    localStorage.setItem('theme', themeName);
    if (themeName == "system") {
        themeName = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute('data-theme', themeName);
}

setTheme(getTheme())

document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("input[name='color_theme']").forEach((input) => {
        if (input.value == getTheme()) {
            input.checked = true;
        }
        input.addEventListener('change', e => setTheme(e.target.value));
    });

    // also check to see if the user changes their theme settings while the page is loaded.
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        setTheme(getTheme());
    })
});
