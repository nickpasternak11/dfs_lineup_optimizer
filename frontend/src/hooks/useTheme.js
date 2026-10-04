import { createContext, useEffect, useState } from 'react';
import { loadTheme, saveTheme } from '../lib/storage';

const systemTheme = () => (
    window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
);

// The active theme, for components that pick theme-specific assets.
export const ThemeContext = createContext('light');

// Follows the system setting until the viewer picks one, then remembers it.
export default function useTheme() {
    const [theme, setTheme] = useState(() => loadTheme() || systemTheme());

    useEffect(() => {
        document.documentElement.dataset.theme = theme;
    }, [theme]);

    const toggleTheme = () => setTheme((prev) => {
        const next = prev === 'dark' ? 'light' : 'dark';
        saveTheme(next);
        return next;
    });

    return { theme, toggleTheme };
}
