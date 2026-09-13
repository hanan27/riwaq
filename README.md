# Riwaq | رواق

A bilingual campus-services assistant for **fictional Namaa University**, built for **SDAIA Academy — LLM Application Engineering (SDA-AIE-213)**. **Track B: Campus services.** It answers grounded questions about admissions, enrolment and transcripts, books an advisor appointment only with authenticated permission and explicit slot confirmation, and hands requests to student support.

**Evidence status:** the included notebook runs without credentials using a clearly labelled deterministic simulator. The application tests are real; live commercial/open-weight model quality, provider caching and dollar costs have not been measured. See [the criteria audit](docs/CRITERIA_AUDIT.md) for the exact remaining requirements.

**Submission identity:** the trainee's full name and cohort dates have not yet been provided. The rubric requires these before grading. This is an unfinished administrative requirement, not invented personal information.

Programme: [SDAIA Academy](https://github.com/SDAIAAcademy). All people, prices, policies and services in this project are fictional.

## Run the notebook

1. Open [Google Colab](https://colab.research.google.com/).
2. Choose **File → Upload notebook** and select `Riwaq_Capstone.ipynb` from this folder.
3. Select **Runtime → Run all**. The notebook embeds its source and data, creates an isolated temporary workspace, and needs no key, clone or package installation for the default run.
4. Read the printed conversation, stage demonstrations, safety results, fault transcript, regression gate, and cost table.
5. Use the optional chat cell for new English or Arabic questions. The booking demonstration uses explicitly fictional trusted sessions.

The notebook has been executed from a fresh local Python process. A Colab browser run is still required before submission; it is not claimed to have happened.

## Run locally

Python 3.10 or later; standard library only:

```bash
python3 scripts/run_checks.py
python3 -m unittest discover -s tests -v
python3 scripts/build_notebook.py
python3 scripts/execute_notebook.py
```

The checks command regenerates `data/golden.json`, `EVALUATION_REPORT.md`, `BENCHMARKS.md` and ignored raw `evidence.json`. The notebook build command embeds current source/data. The execution command runs all cells in order in a clean temporary directory and captures outputs in the notebook. No reference Murshid files are modified.

## What to read

- `Riwaq_Capstone.ipynb`: the main submission, implementation, demonstrations and explanations.
- [Step-by-step guide](docs/STEP_BY_STEP.md): beginner explanation, commands and defence questions.
- [Technical documentation](docs/TECHNICAL.md): architecture, trust boundaries, state and interfaces.
- [Evaluation report](EVALUATION_REPORT.md): measured offline slices, provenance and limitations.
- [Benchmarks](BENCHMARKS.md): extraction/guard/cache evidence without invented live numbers.
- [Decisions](docs/DECISIONS.md): architecture, routing, trade-offs and economics.
- [Criteria audit](docs/CRITERIA_AUDIT.md): all seven sections and remaining gaps.

## Optional live runs

The final notebook sections explain commercial/open-weight environment configuration. Configure provider URLs, model IDs and keys privately through Colab Secrets or environment variables; never paste keys into source or output. A deliberate live run consumes the account's quota. Default Run all performs no network requests.

The adapter uses the documented [OpenAI-compatible vLLM Chat API](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/). Provider cache usage is read from the response rather than assumed; see [provider prompt-cache accounting](https://openai.com/index/api-prompt-caching/). Endpoint/model compatibility must be checked during the live run.

## Attribution

The assignment and architectural disciplines come from the supplied SDAIA course. Riwaq's domain implementation, datasets and notebook are newly created; this is not Murshid with a replacement directory. Implementation and documentation were prepared with AI assistance at the trainee's request. The trainee must review the code, independently approve evaluation expectations, and be able to explain the submitted work.
