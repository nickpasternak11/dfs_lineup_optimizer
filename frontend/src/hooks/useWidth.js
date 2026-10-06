import { useEffect, useRef, useState } from 'react';

// Width of the element, kept current as it resizes; the SVG is laid out in
// real pixels so its text never scales.
export default function useWidth(fallback) {
    const ref = useRef(null);
    const [width, setWidth] = useState(fallback);
    useEffect(() => {
        const element = ref.current;
        if (!element) return undefined;
        setWidth(element.clientWidth || fallback);
        if (typeof ResizeObserver === 'undefined') return undefined;
        const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width || fallback));
        observer.observe(element);
        return () => observer.disconnect();
    }, [fallback]);
    return [ref, width];
}
