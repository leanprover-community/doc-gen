const toggleSwitch = document.querySelector('#theme_toggler');
// the theme varaible is guarenteed to have a value since detect_color_scheme defines it
// and is run before.

function switchTheme(e) {
    theme = (theme == "dark") ? "light" : "dark";
    setTheme(theme);
}

function setTheme(themeName) {
    if (themeName == "light") {
        localStorage.setItem('theme', 'light');
        document.documentElement.setAttribute('data-theme', 'light');
    } else {
        localStorage.setItem('theme', 'dark');
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

toggleSwitch.addEventListener('click', switchTheme, false);

// also check to see if the user changes their theme settings while the page is loaded.
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    var newTheme = event.matches ? "dark" : "light";
    setTheme(newTheme);
})