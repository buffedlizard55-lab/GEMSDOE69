# gems69_s3: pinned lane modules for the session-3 experiments (H69-M, H69-N)

These are byte-exact copies of `src/gems69/*.py` at base commit `04b46c1`. The session-3
preregistered gates (`evidence/h69m_gate.json`, `evidence/h69n_gate.json`) were run against
these files. The two selectors (`evidence_first.py`, `evidence_quota.py`) were written in
session 3 and moved here unchanged by `git mv`.

Why a snapshot: while session 3 ran, main merged the H69-G5 rewrite of `src/gems69`
(corridors, scoring, physics, tips, holdout69, data). That rewrite removed names the session-3
selectors import (e.g. `scoring.LIDAR_LAYERS`) and changed corridor geometry. Pointing the
session-3 runners at the new modules would make the committed code differ from the code that
produced the gate numbers. The shared template tools (`vendor/template66`: gems57 holdout,
uniqueness, submission writer) are NOT forked; both code paths use them unchanged.

Use `src/gems69` for new work. Use `gems69_s3` only to reproduce session-3 results
(`scripts/run_h69m.py`, `scripts/run_h69n.py`, `scripts/uniqueness_h69m.py`).
