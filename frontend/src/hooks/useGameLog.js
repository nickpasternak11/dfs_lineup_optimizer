import { useEffect, useState } from 'react';
import { errorMessage, fetchDstGameLog, fetchPlayerGameLog } from '../api/client';

// Game logs change once a day at most; keep each one for the session so
// reopening a player is instant.
const cache = new Map();

export const gameLogKey = player => (
    player.position === 'DST' ? `dst:${player.team}` : player.gsis_id && `player:${player.gsis_id}`
);

// { status: 'loading' | 'ready' | 'unlinked' | 'error', data, error } for the
// player whose popup is open. Players we couldn't match to nflverse have no
// id to ask for, so they come back 'unlinked' without a request.
export default function useGameLog(player) {
    const key = player ? gameLogKey(player) : null;
    const [state, setState] = useState({ status: 'loading' });

    useEffect(() => {
        if (!player) return undefined;
        if (!key) {
            setState({ status: 'unlinked' });
            return undefined;
        }
        if (cache.has(key)) {
            setState({ status: 'ready', data: cache.get(key) });
            return undefined;
        }
        let current = true;
        setState({ status: 'loading' });
        const request = player.position === 'DST' ? fetchDstGameLog(player.team) : fetchPlayerGameLog(player.gsis_id);
        request
            .then((data) => {
                cache.set(key, data);
                if (current) setState({ status: 'ready', data });
            })
            .catch((error) => {
                // A 404 means nflverse has nothing for them yet (a rookie
                // before his first game, or a DST with no games this season).
                const missing = error.response?.status === 404;
                if (current) {
                    setState(missing
                        ? { status: 'ready', data: { player: null, games: [] } }
                        : { status: 'error', error: errorMessage(error, 'Could not load the game log.') });
                }
            });
        return () => { current = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [key]);

    return state;
}
