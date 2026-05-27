document.addEventListener('DOMContentLoaded', () => {
    const root = document.documentElement;
    const storedTheme = localStorage.getItem('labtrack-theme');
    const preferredTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
    const initialTheme = storedTheme || preferredTheme;

    const applyTheme = (theme) => {
        root.dataset.theme = theme;
        localStorage.setItem('labtrack-theme', theme);

        document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
            const icon = button.querySelector('i');
            if (!icon) {
                return;
            }

            icon.className = theme === 'light' ? 'bi bi-sun' : 'bi bi-moon-stars';
        });
    };

    applyTheme(initialTheme);

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
        button.addEventListener('click', () => {
            const nextTheme = root.dataset.theme === 'light' ? 'dark' : 'light';
            applyTheme(nextTheme);
        });
    });
});