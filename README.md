# Riwaq | رواق

Bilingual fictional campus-services assistant by Hanan Ahmed Alahmadi.

**Open `Riwaq_Capstone.ipynb` to review the executed submission.** Its saved outputs and `EVALUATION_REPORT.md` contain the real run. The embedded source/configuration is authoritative for this saved run.

## Runbook

For reproduction: upload the submitted notebook to Colab, select a T4 GPU, add `HF_TOKEN` to Colab Secrets with notebook access, then choose **Run all**. Hugging Face credits/billing apply. No additional run is needed to inspect the saved submission.

The submitted hosted model is `openai/gpt-oss-20b` via Hugging Face's router, using DeepInfra primary and Together fallback through the OpenAI SDK. Local Qwen2.5-1.5B runs directly in Transformers. Model aliases, rates and the $1/hour hardware assumption appear in the notebook's configuration output.

## Demo and results

The notebook's final documentation section walks through recorded English and Arabic FAQ, booking and handoff cases. It is a saved-case walkthrough, not a new conversation run.

**Known limitations:** hosted calls failed; Qwen scored 71.4% overall and 5% on FAQs; R079 made an incorrect booking. Both regression gates failed. Human judge calibration, observed provider caching and measured hosted break-even remain incomplete.

- `DECISIONS.md`: architecture and model-choice rationale.
- `EVALUATION_REPORT.md` and `run-results.json`: report and original raw evidence.
- `QWEN_REQUEST_COSTS.csv`: modeled local per-call costs derived from saved timings; not an invoice.

Post-run changes are documentation and arithmetic only. Executed code, outputs, expectations and measurements are preserved.
