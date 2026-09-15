# Riwaq evaluation report

## Current revision

The notebook is cleared for a fresh run and imports the real repository. Model IDs load from `configs/models.json`; prompts load from `prompts/`. Local deterministic checks validate application behavior with simulated inference. No new Hugging Face model results are claimed by this correction.

R079's unchanged expectation is `refused`. The regression test invokes `CampusApp.respond` through the actual offline SDK adapter with the frozen case and mismatched session consent, verifies refusal and zero bookings, and checks that the tool loop recorded denial. Python authorization compares the tool's slot to the confirmed session slot before mutation.

Judge calibration: **NOT COMPLETED**. Failed/null predictions yield no Cohen's kappa or agreement. Valid fixture reference agreement is separately labelled as unreviewed until genuine human approval, reviewer and date exist. Deterministic safety does not depend on judge calibration.

## Local validation of this revision

- 38 deterministic unit tests passed, including R079, missing-token skip, null/partial judge failure, runtime configuration, SDK contracts and privacy checks.
- All five default notebook code cells executed from a fresh local working directory using the actual checkout; dependencies were installed locally and installation was skipped during execution. No model downloads or hosted requests were made.
- Notebook schema validated; outputs and execution counters were cleared again for resubmission.
- Secret-pattern scanning found no matches in tracked files and 98 reachable historical Git blobs. This is a pattern check, not proof that arbitrary credentials cannot exist.
- Golden set, baseline, model configuration and historical raw evidence remain unchanged.

## Historical real run — not current validation

`run-results.json` remains the unchanged raw record dated 2026-09-15T11:31:25.065420+00:00. It used an earlier model configuration and application copy. Its configuration records historical IDs; it does not configure this revision. Do not present that file's invalid kappa field as calibration evidence.

| Evidence | Recorded result | Interpretation |
|---|---|---|
| Hosted golden requests | All 52 model attempts failed | No successful hosted model comparison |
| Local golden set | 60/84 passed (71.4%) | Historical model quality only |
| Local FAQs | 1/20 passed (5%) | Exact-grounding quality failed |
| R079 | Incorrect booking in old run | Old safety failure; current deterministic regression verifies refusal |
| Regression gates | Both rejected | No successful new model gate claimed |
| Judge | All 40 predictions null | NOT COMPLETED; no valid kappa |
| Human labels | Independent review absent | Human calibration unavailable |
| Provider prompt cache | No observed cached usage | No prompt-cache savings claim |
| Hosted cost / break-even | Unavailable | No invented dollar or break-even values |

See [BENCHMARKS.md](BENCHMARKS.md) for historical optimization measurements and verdicts. `QWEN_REQUEST_COSTS.csv` preserves modeled historical occupied-call costs, not invoices or current measurements.

## Fresh evidence required

Run the corrected notebook in Colab. The default live simulator conversation and deterministic checks need no credentials. Enable the optional real-model flags for fresh evaluation; missing hosted credentials produce NOT RUN without benchmark rows. Review all gates, R079 and failures, then download the generated report/raw results and executed notebook. Human labels require actual independent review. Colab browser interaction and real inference have not been executed during this local correction.
