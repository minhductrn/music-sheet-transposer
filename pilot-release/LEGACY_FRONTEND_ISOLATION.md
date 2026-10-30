# Legacy frontend isolation

Date: October 30, 2026.

The Product Owner requested isolation of the retired frontend/ so it no longer needs synchronization with GitHub. Root package scripts already use frontend-v2/. No active application entry point was changed.

A verified local source archive contains all legacy source files, including uncommitted work; dependencies and generated dist output are excluded. It is stored outside the repository at /home/dtran/music-sheet-transposer-legacy-archive/frontend-before-isolation-2026-10-30/. Its manifest records every source file and the archive SHA-256.

Git index removal uses --cached: local legacy files remain unchanged. The /frontend/ ignore rule prevents reintroduction. Historical commits are retained. Classic packages, UX Next application code, private scores and other pending work remain unchanged.

The isolation is prepared in the original local checkout and on the independent UX Next branch. No commit or push is performed by this preparation step; remote branch contents change only after a subsequent authorized commit/push.
