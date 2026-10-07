import { useEffect, useState } from 'react';

// The app's two pages, addressed by the URL hash so they can be bookmarked
// and the back button moves between them: #/ (lineups) and #/accuracy.
export const VIEWS = {
    lineups: { hash: '#/', title: 'DFS Lineup Optimizer' },
    accuracy: { hash: '#/accuracy', title: 'Projection accuracy · DFS Lineup Optimizer' },
};

export const viewFromHash = hash => (hash === VIEWS.accuracy.hash ? 'accuracy' : 'lineups');

export default function useView() {
    const [view, setView] = useState(() => viewFromHash(window.location.hash));

    useEffect(() => {
        const onHashChange = () => {
            setView(viewFromHash(window.location.hash));
            window.scrollTo(0, 0);
        };
        window.addEventListener('hashchange', onHashChange);
        return () => window.removeEventListener('hashchange', onHashChange);
    }, []);

    useEffect(() => {
        document.title = VIEWS[view].title;
    }, [view]);

    return view;
}
