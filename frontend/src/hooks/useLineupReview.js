import { useEffect, useState } from 'react';
import { errorMessage, fetchLineupReview } from '../api/client';

// { status: 'loading' | 'ready' | 'error', data, error } for one week's
// review (the latest saved week when year and week are null). The previous
// review stays on screen while the next loads.
export default function useLineupReview(year, week) {
    const [state, setState] = useState({ status: 'loading', data: null });

    useEffect(() => {
        let current = true;
        setState(prev => ({ status: 'loading', data: prev.data }));
        fetchLineupReview({ year, week })
            .then((data) => {
                if (current) setState({ status: 'ready', data });
            })
            .catch((error) => {
                if (current) {
                    setState(prev => ({
                        status: 'error',
                        data: prev.data,
                        error: errorMessage(error, 'Could not load the saved lineups.'),
                    }));
                }
            });
        return () => { current = false; };
    }, [year, week]);

    return state;
}
