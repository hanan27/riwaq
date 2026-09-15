# Colab result review

**Historical evidence:** this records the version before the 15 September SDK/Pydantic upgrade. The updated notebook has separate local verification and needs a new Colab Run all.

Reviewed the user-provided `Riwaq_Capstone_reults.ipynb` on 2026-09-14. The original returned notebook is preserved unchanged.

- All 19 code cells have sequential execution counts 1–19 and no recorded error outputs.
- Colab output metadata is present. Code cells match the supplied project notebook exactly.
- The bilingual conversation, authorized booking, refusal and handoff completed.
- Golden evaluation: 84/84 passed, including 40/40 safety cases.
- Tool/output/indirect-injection tests: 18/18 passed.
- Guard results: 32/32 attacks blocked; 0/32 legitimate requests blocked.
- Clean regression gate allowed the baseline; seeded Arabic regression was rejected.
- Cache replay: 100 → 20 → 18 model calls; zero wrong hits on eight near-miss pairs. This is an 82% call-count reduction, not measured dollar savings.
- Live commercial/open-weight inference, live judge calibration and real cost/hosting measurements were explicitly skipped.

This supports successful default execution in Colab. The saved notebook cannot independently establish whether the runtime was reset immediately before execution. Its T4 GPU metadata does not establish that model weights ran: this execution used the offline simulator.

Notebook SHA-256: `2ef83744a12d65c698548e01bf5f0b28cfdc1f86b8e5f4d827964b389895996e`.
