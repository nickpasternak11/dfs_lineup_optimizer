import React from 'react';

// Inline SVG icons (Lucide-style strokes), so they render the same everywhere,
// unlike emoji, and inherit the surrounding text color.
const PATHS = {
    lock: <><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>,
    unlock: <><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 7.9-1" /></>,
    ban: <><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></>,
    undo: <><path d="M9 14 4 9l5-5" /><path d="M4 9h11a5 5 0 0 1 0 10h-3" /></>,
    refresh: <><path d="M21 12a9 9 0 1 1-2.6-6.4" /><path d="M21 4v5h-5" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
    close: <path d="M18 6 6 18M6 6l12 12" />,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
    moon: <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z" />,
    copy: <><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" /></>,
    check: <path d="m5 12 5 5L20 7" />,
    sortUp: <path d="m7 14 5-5 5 5" />,
    sortDown: <path d="m7 10 5 5 5-5" />,
    sort: <><path d="m8 9 4-4 4 4" /><path d="m16 15-4 4-4-4" /></>,
};

export default function Icon({ name, size = 16, className = '', title }) {
    return (
        <svg
            className={`icon ${className}`.trim()}
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden={title ? undefined : true}
            role={title ? 'img' : undefined}
        >
            {title && <title>{title}</title>}
            {PATHS[name]}
        </svg>
    );
}
