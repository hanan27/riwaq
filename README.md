# Riwaq | رواق

A bilingual campus-services assistant for **fictional Namaa University**, built for **SDAIA Academy — LLM Application Engineering (SDA-AIE-213)**. **Track B: Campus services.** It answers grounded questions about admissions, enrolment and transcripts, books an advisor appointment only with authenticated permission and explicit slot confirmation, and hands requests to student support.

**Evidence status:** the notebook starts with clearly labelled offline code checks, then automatically runs a public Hugging Face model when opened in a Colab GPU runtime. No paid API or token is required for this local route. Actual GPU execution of this newest version is pending; the earlier application-only Colab run passed. The application tests are real; live commercial/open-weight model quality, provider caching and dollar costs have not been measured. See [the criteria audit](docs/CRITERIA_AUDIT.md) for the exact remaining requirements.

**Trainee:** Hanan Ahmed Alahmadi  
**Cohort dates:** 13–16 September 2026

Programme: [SDAIA Academy](https://github.com/SDAIAAcademy). All people, prices, policies and services in this project are fictional.

## Run the notebook

1. Open [Google Colab](https://colab.research.google.com/).
2. Choose **File → Upload notebook** and select `Riwaq_Capstone.ipynb` from this folder.
3. Select **Runtime → Change runtime type → T4 GPU**, then **Runtime → Run all**. The notebook embeds its source and data, creates an isolated temporary workspace, and needs no key or manual setup. The first cell installs pinned SDK dependencies if missing. Section 12 installs an isolated vLLM environment and downloads public model weights; allow several minutes and keep the runtime connected.
4. Read the printed conversation, stage demonstrations, safety results, fault transcript, regression gate, and cost table.
5. Save the automatically downloaded `Riwaq_results.zip`, then download the executed notebook. Use `Riwaq_Human_Review.html` to supply your independent review. The chat cell now uses the local model after it starts. The booking demonstration uses explicitly fictional trusted sessions.

The prior upgraded notebook passed all 21 code cells. The new Hugging Face integration is locally tested, but its GPU execution cannot be performed on this Mac. The original 19-cell run is preserved in Git history. The newer returned 21-cell run is preserved in `evidence/notebooks/colab_before_huggingface.ipynb`. The preserved earlier SDK/Pydantic notebook records all 21 cells completing successfully in Colab; see [updated verification](docs/COLAB_UPGRADE_VERIFICATION.md). See [Colab verification](docs/COLAB_VERIFICATION.md); a runtime reset cannot be independently established from saved outputs.

## Run locally

Python 3.10 or later, using the pinned dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_checks.py
python3 -m unittest discover -s tests -v
python3 scripts/build_notebook.py
python3 scripts/execute_notebook.py
```

The checks command verifies the frozen golden set and baseline, then regenerates `EVALUATION_REPORT.md`, `BENCHMARKS.md` and ignored raw `evidence.json`. It does not modify expectations or promote the baseline. The notebook build command embeds current source/data. The execution command runs all cells in order in a clean temporary directory and captures outputs in the notebook. No reference Murshid files are modified.

## Finish the no-paid-API workflow

Read [FINISHING_STEPS.md](docs/FINISHING_STEPS.md). The notebook now starts local inference, evaluates the frozen cases, measures cache/throughput, creates a human-review form, and exports reports. Your earlier returned notebook is preserved under `evidence/notebooks/colab_before_huggingface.ipynb`.

The rubric separately names a commercial comparison. A public open-weight model does not satisfy that item by itself, and no instructor waiver has been invented.

## What changed for the detailed rubric

Pydantic validators, strict JSON-schema requests, an SDK-driven tool loop, versioned prompt files, Saudi PII masking, a written judge rubric and a committed regression baseline are now implemented and tested. See [every grading-engine criterion](docs/GRADING_ENGINE_AUDIT.md). Live measurements and independent human review remain outstanding.

## What to read

- `Riwaq_Capstone.ipynb`: the main submission, implementation, demonstrations and explanations.
- [Step-by-step guide](docs/STEP_BY_STEP.md): beginner explanation, commands and defence questions.
- [Technical documentation](docs/TECHNICAL.md): architecture, trust boundaries, state and interfaces.
- [Evaluation report](EVALUATION_REPORT.md): measured offline slices, provenance and limitations.
- [Benchmarks](BENCHMARKS.md): extraction/guard/cache evidence without invented live numbers.
- [Decisions](docs/DECISIONS.md): architecture, routing, trade-offs and economics.
- [Criteria audit](docs/CRITERIA_AUDIT.md): all seven sections and remaining gaps.

## Optional live runs

The final notebook sections explain commercial/open-weight environment configuration. Configure provider URLs, model IDs and keys privately through Colab Secrets or environment variables; never paste keys into source or output. A deliberate live run consumes the account's quota. In Colab, default Run all downloads and serves an actual public Hugging Face model locally. On a non-Colab host it clearly skips that GPU step. The initial deterministic checks still use a labelled SDK mock transport.

The adapter follows the official [strict structured-output](https://developers.openai.com/api/docs/guides/structured-outputs) and [function-calling](https://developers.openai.com/api/docs/guides/function-calling) contracts, using the OpenAI SDK. It can target the documented [OpenAI-compatible vLLM Chat API](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/). Provider cache usage is read from the response rather than assumed; see [provider prompt-cache accounting](https://openai.com/index/api-prompt-caching/). Endpoint/model compatibility must be checked during the live run.

## Attribution

The assignment and architectural disciplines come from the supplied SDAIA course. Riwaq's domain implementation, datasets and notebook are newly created; this is not Murshid with a replacement directory. Implementation and documentation were prepared with AI assistance at the trainee's request. The trainee must review the code, independently approve evaluation expectations, and be able to explain the submitted work.
