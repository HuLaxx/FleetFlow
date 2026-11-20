# P0 source hygiene — 20 November 2026

The Git tree historically tracked Python 3.10 compiled bytecode across backend and ml even though `.gitignore` included `__pycache__` and `*.pyc`. Ignore rules **do not untrack previously committed files**. This review PR deletes 21 tracked bytecode blobs from the branch and installs a Git-index CI assertion that rejects any future tracked compiled Python files. No application source behavior is changed. This does not rewrite past Git commits; old historical blobs remain in Git history. Exact-head CI must pass before this is treated as verified.
