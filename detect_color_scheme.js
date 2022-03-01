var theme="light"; // by default it's light theme.

var storedTheme = localStorage.getItem("theme")
var OSThemeIsDark = window.matchMedia("(prefers-color-scheme: dark)").matches

// If they have stored settings, use those. Otherwise use their OS's theme.
if (storedTheme) {
    theme = storedTheme
} else if (OSThemeIsDark) {
    theme = "dark"
}

// this changes the value of the css varaibles to make it dark
if (theme=="dark") {
    document.documentElement.setAttribute("data-theme", "dark");
}