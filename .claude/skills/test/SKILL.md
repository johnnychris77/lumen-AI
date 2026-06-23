# /test — Run the LumenAI test suite

cd to `/home/user/lumen-AI/backend`, then run:

```bash
python -m pytest tests/ -q
```

Report only genuine failures. Ignore collection errors that say `No module named 'app'` — those mean pytest was invoked from the wrong directory, not that anything is broken. If you see them, confirm you are in `backend/` and re-run.

After the run, print a one-line summary: how many passed, how many failed (real failures only), and whether the suite is green.
