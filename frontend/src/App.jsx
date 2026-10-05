import React, { useCallback, useState } from 'react';
import { ToastContainer } from 'react-toastify';
import AppHeader from './components/header/AppHeader';
import LineupPanel from './components/lineups/LineupPanel';
import PlayerModal from './components/player/PlayerModal';
import PlayerPool from './components/pool/PlayerPool';
import useOptimizer from './hooks/useOptimizer';
import usePlayerPool from './hooks/usePlayerPool';
import useTheme, { ThemeContext } from './hooks/useTheme';
import './styles/theme.css';
import './App.css';

export default function App() {
    const { theme, toggleTheme } = useTheme();
    const optimizer = useOptimizer();
    const playerPool = usePlayerPool({
        pool: optimizer.pool,
        lineups: optimizer.lineups,
        locked: optimizer.locked,
        excluded: optimizer.excluded,
        includeStarted: optimizer.includeStarted,
        isPastSlate: optimizer.isPastSlate,
    });
    const [openPlayer, setOpenPlayer] = useState(null);
    const closePlayer = useCallback(() => setOpenPlayer(null), []);

    return (
        <ThemeContext.Provider value={theme}>
            <AppHeader
                slate={optimizer.slate}
                current={optimizer.current}
                onChangeSlate={optimizer.changeSlate}
                theme={theme}
                onToggleTheme={toggleTheme}
            />
            <main className="app-layout">
                <PlayerPool optimizer={optimizer} playerPool={playerPool} onOpenPlayer={setOpenPlayer} />
                <aside className="app-sidebar">
                    <LineupPanel optimizer={optimizer} onReviewExcluded={() => playerPool.setFilter('quick', 'excluded')} />
                </aside>
            </main>
            {openPlayer && (
                <PlayerModal
                    player={openPlayer}
                    unavailableReason={playerPool.unavailableReason(openPlayer)}
                    optimizer={optimizer}
                    slateYear={optimizer.slate.year}
                    onClose={closePlayer}
                />
            )}
            <ToastContainer position="bottom-right" theme={theme} autoClose={4000} />
        </ThemeContext.Provider>
    );
}
