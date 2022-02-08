//identify the toggle switch HTML element
const toggleSwitch = document.querySelector('#theme_toggler');
var toggled = false;

//function that changes the theme, and sets a localStorage variable to track the theme between page loads
function switchTheme(e) {
    if (toggled) {
        localStorage.setItem('theme', 'dark');
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
        document.documentElement.setAttribute('data-theme', 'light');
    }    
    toggled = !toggled;
}

toggleSwitch.addEventListener('click', switchTheme, false);

// also check to see if the user changes their theme settings while the page is loaded.
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    if (event.matches) {
     document.documentElement.setAttribute("data-theme", "dark");
    } else {
     document.documentElement.setAttribute("data-theme", "light");
    }
})

