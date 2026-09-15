# Riwaq | رواق

A bilingual Arabic–English assistant for fictional campus services by Hanan Ahmed Alahmadi. It answers grounded FAQs, books advising appointments with explicit session consent, and hands requests to support.

Capstone for **LLM Application Engineering — SDA-AIE-213**, [SDAIA Academy](https://github.com/SDAIAAcademy). Cohort dates are not recorded in the available course information.

## Run in Colab

1. Push this corrected repository to GitHub before opening the notebook: Colab executes files from that repository.
2. Open [Riwaq in Colab](https://colab.research.google.com/github/hanan27/riwaq/blob/main/Riwaq_Capstone.ipynb). If your submission branch differs, select it in Colab's GitHub notebook picker.
3. Choose **Runtime → Run all**. Default setup needs internet for checkout/dependencies, but **no secret and no GPU**. The setup prints the checkout path and commit for verification. On a reused runtime, delete `/content/riwaq` or disconnect/delete the runtime before opening the corrected version.
4. Find **Live bilingual conversation — simulator** below the safety checks. Read the fresh English/Arabic examples, then type a message and click **Send**. For a fictional booking, choose a slot and tick the consent checkbox. Consent resets after each message.
5. Inspect the **Production request stages** cell. It calls the real input, routing, context, execution and output functions from `src/riwaq.py`.

The default conversation uses deterministic simulated model responses through the existing SDK mock transport. It is a live application demonstration, not evidence of LLM quality. Bookings and sessions are fictional and in memory.

### Optional real model evaluation

In **Optional real Hugging Face evaluation**, set `RUN_HOSTED = True` and/or `RUN_LOCAL_MODEL = True`, then rerun that cell. For local weights select a T4 GPU first; downloading public weights requires no token. For hosted inference add `HF_TOKEN` privately in Colab Secrets and enable notebook access. Hosted use may incur Hugging Face charges. Missing credentials report **NOT RUN** without synthetic error benchmarks.

`configs/models.json` is the single source of truth for model IDs and routes. Both hosted and local adapters read it at runtime. The existing OpenAI Python SDK only transports requests to Hugging Face's compatible endpoint; this project does not call OpenAI's service. Configured catalog prices are historical assumptions, not verified current prices or invoices.

Download the executed notebook via **File → Download → Download .ipynb**. After optional evaluation, download `EVALUATION_REPORT.md` and `run-results.json` from the Files panel under `riwaq`. Inspect failed gates and pending evidence before resubmitting. Never commit tokens.

## Local checks

```bash
python -m pip install -r requirements-demo.txt
python scripts/run_checks.py
python scripts/build_notebook.py
```

The notebook imports readable `src/`, `prompts/`, `data/` and `configs/` directly. No second project copy is packaged inside it. Prompts are versioned JSON files; logs retain prompt IDs/hashes. Python session/tool authorization rejects mismatched consent, including frozen golden case R079.

## Evidence and limitations

- [EVALUATION_REPORT.md](EVALUATION_REPORT.md): current evidence status and historical limitations.
- [BENCHMARKS.md](BENCHMARKS.md): measured versus unavailable economics and optimization verdicts.
- [DECISIONS.md](DECISIONS.md): architecture and safety rationale.
- `run-results.json` and `QWEN_REQUEST_COSTS.csv`: unchanged **historical** evidence from the earlier implementation/configuration, not validation of this revision. Historical model IDs and the invalid null-prediction kappa are retained only as raw provenance.

The previous real run failed both regression gates and incorrectly booked R079. Current deterministic tests verify refusal, but fresh real-model evaluation is still needed. Judge calls previously failed; human calibration is NOT COMPLETED. Provider prompt-cache savings, hosted dollar costs and measured break-even are unavailable. Local simulated success cannot establish model quality. Exact FAQ grounding intentionally rejects paraphrases. The Colab browser UI still requires manual verification.
