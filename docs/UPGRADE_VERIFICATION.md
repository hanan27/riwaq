# Upgrade verification — 15 September 2026

Evidence is from executed application code and an **offline SDK transport**, not model weights or a commercial service.

- 21 notebook code cells completed in order from a fresh local process; outputs are saved.
- 84/84 original golden cases passed; 40/40 safety cases passed. The original golden data is unchanged.
- 32/32 attack cases blocked and 0/32 legitimate requests incorrectly blocked.
- 18 original tool/output/indirect-injection safety tests passed.
- 12/12 Saudi-format privacy cases passed; no raw fixture PII reached model inputs or metadata logs.
- 25 additional contract and boundary tests passed, including actual SDK invocation, strict schema on the serialized request, tool-result round trips, authorization, bounded calls, error feedback, cache isolation and frozen baseline behavior.
- Clean gate passed; deliberately degraded Arabic prompt was rejected against the frozen baseline file.
- Before/after FAQ replay retained evaluation/safety verdicts with 100 → 20 → 18 model calls. Dollar savings remain unknown.
- The user's earlier Colab results notebook is unchanged and remains historical evidence for the previous version.

Reproduce locally after installing `requirements.txt`:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_checks.py
python3 scripts/build_notebook.py
python3 scripts/execute_notebook.py
```

Pending external evidence: fresh Colab execution of this upgraded notebook, live commercial/open-weight runs, independent human-label review and live judge calibration, provider cached-token observation, actual dollar/hosting measurements, GitHub publication and peer review. See the full [grading-engine audit](GRADING_ENGINE_AUDIT.md).
