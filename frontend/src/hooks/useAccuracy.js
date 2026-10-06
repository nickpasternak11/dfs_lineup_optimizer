import { useEffect, useState } from 'react';
import { errorMessage, fetchAccuracy } from '../api/client';

// The report changes at most once a day, so each filter combination is kept
// for the session and flipping back to one is instant.
const cache = new Map();

// For tests: each starts with nothing cached.
export const clearAccuracyCache = () => cache.clear();

const keyOf = ({ view, year, position, minProj }) => `${view}|${year ?? 'all'}|${position ?? 'all'}|${minProj}`;

// { status: 'loading' | 'ready' | 'error', data, error }. While a new filter
// loads, the previous report stays on screen (status 'loading', data set) so
// the page doesn't flash empty.
export default function useAccuracy(filters) {
    const key = keyOf(filters);
    const [state, setState] = useState(() => (
        cache.has(key) ? { status: 'ready', data: cache.get(key) } : { status: 'loading', data: null }
    ));

    useEffect(() => {
        if (cache.has(key)) {
            setState({ status: 'ready', data: cache.get(key) });
            return undefined;
        }
        let current = true;
        setState(prev => ({ status: 'loading', data: prev.data }));
        fetchAccuracy(filters)
            .then((data) => {
                cache.set(key, data);
                if (current) setState({ status: 'ready', data });
            })
            .catch((error) => {
                if (current) {
                    setState(prev => ({
                        status: 'error',
                        data: prev.data,
                        error: errorMessage(error, 'Could not load projection accuracy.'),
                    }));
                }
            });
        return () => { current = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key]);

    return state;
}
