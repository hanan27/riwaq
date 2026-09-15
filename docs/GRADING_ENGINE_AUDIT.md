# Detailed grading-engine audit — 15 September 2026 upgrade

This maps the user's newly supplied grading-engine breakdown to the actual implementation. **Implemented** means code exists and has executed in local tests. It does not mean live provider evidence or a particular mark has been earned. The default path calls the real OpenAI SDK through an explicitly simulated transport; no model weights run by default.

| Criterion | Points | Evidence and status |
|---|---:|---|
| Provider SDK actually called | 3 | `HTTPClient` invokes `sdk.chat.completions.create`; default SDK transport and contract tests execute it. **Live inference pending.** |
| Typed boundary | 4 | `LLMClient` Protocol; business stages depend on `MeteredClient`, with SDK imports restricted to adapter. |
| Model IDs from configuration | 4 | Offline alias in `configs/models.json`; live model IDs and fallback aliases from environment configuration. |
| Retry, backoff, fallback | 2 | SDK internal retries disabled; boundary retries rate limits with bounded exponential-delay policy, switches on outage, and logs attempts. Fault and transport tests executed. |
| Decisions record | 2 | `docs/DECISIONS.md` includes original ADRs and the rubric upgrade. Production model choice awaits measured comparison. |
| Pydantic contract and validators | 4 | `AppointmentRequest`, `FAQAnswer`, `JudgeVerdict`, tool argument models; strict types, forbidden extras, slot and nonblank validators. |
| Schema generation over wire | 3 | Actual SDK request contains `response_format.type=json_schema`, strict true, Pydantic schema. Tool definitions also use strict schemas. Transport test inspects serialized body. **Live acceptance pending.** |
| Validate → retry → repair | 4 | Pydantic validation errors carry field location, error type and message into retries; raw invalid values omitted and PII masked. |
| Real tool definitions and execution loop | 2 | Model `tool_calls` decoded and executed; assistant calls and `role=tool` results returned on subsequent model requests. SDK round-trip tests executed. |
| Bounded authorized actions | 2 | At most three tool rounds plus one final acknowledgement; one call per round; role/identity/consent checks; changed slots refused; handoff terminal. |
| Versioned file prompts | 4 | `prompts/*.json` are loaded from disk with changelogs; tool descriptions in versioned config; written judge rubric in `eval/rubrics`. |
| Bilingual deterministic injection wall | 3 | 32 Arabic/English attack cases, 32 legitimate traps, normalization and paired rates. |
| Saudi PII detection and masking | 3 | `privacy.py`: ID/iqama, Saudi phone, IBAN and email formats; Arabic digits and separators; masking before SDK and logs. Twelve data-driven cases plus SDK boundary tests. |
| Outbound PII and prompt leak wall | 3 | Canary, prompt text, injection patterns, PII formats and exact grounded source checks. Negative outputs tested. |
| Named pipeline stages | 2 | Five named methods independently demonstrated in notebook cells. |
| Versioned stratified golden data | 5 | `data/golden.json`: original 84-case set, 48 Arabic, 40 safety; dataset identity checked against seeds. **Owner review remains pending.** |
| Real application harness | 4 | `run_golden` calls the same `CampusApp.respond` used for chat. |
| Deterministic safety assertions | 3 | Safety stratum, authorization, schema, privacy, canary and tool tests; any failure stops execution. |
| LLM judge and written dimension rubric | 3 | `judge.v1` uses strict binary verdict; loaded `groundedness.v1.md` scores factual support alone. **Live judge run pending.** |
| Human calibration, agreement, κ | 3 | Code validates human approval/provenance and both classes; reports agreement, Cohen's κ, confusion matrix. **Independent human labels and measured calibration pending.** |
| Gate against committed baseline | 2 | `data/baseline.v1.json` frozen from a passing SDK-simulator run; identity and slices compared; seeded regression rejected. Ordinary runs do not promote baseline. |
| Usage converted to cost | 4 | Per-attempt input/output/cached usage and price record. Transport fixture tests arithmetic; errors or missing usage retain unknown cost. **Real provider costs pending.** |
| Prompt cache observed | 3 | Separate `cached_usage_observed` flag; absent field stays unknown, never assumed zero/hit. **Actual provider cache observation pending.** |
| Stable prefix and volatile tail | 2 | Static file prompt first; masked request and tool messages afterward. Prefix content hash logged; documented in ADR. |
| Correct response-cache key | 3 | Query, language, source, catalog version, prompt identity, backend endpoint/model and guard version; only public FAQ cached. |
| Cost before/after with eval | 3 | Executed offline call-count table includes each eval verdict. Live replay writes dollars/eval to reports. **Measured dollar table pending.** |
| Commercial and open-weight golden runs | 4 | Configuration and shared harness ready. **Both live runs pending.** |
| Comparison by slice | 3 | Live report writer includes intent/language/risk/difficulty slices plus latency/cost. **Live comparison data pending.** |
| Measured self-host break-even | 3 | Actual open-weight request timing path and both uncached/cached API comparisons implemented. **Isolated self-host measurements/prices pending.** |
| Runnable README/notebook | 4 | Updated self-contained notebook, automatic dependency installation, bilingual demo and explanations. **New Colab rerun needed after this code change.** |
| Single entry point | 3 | Colab Runtime → Run all. No API key required for default SDK simulator. |
| Generated evaluation report | 3 | Offline report generated from actual application runs; live sections generated when enabled; limitations explicit. |

## Submission requirements outside the point rows

Hanan Ahmed Alahmadi; SDAIA Academy, LLM Application Engineering (SDA-AIE-213), cohort 13–16 September 2026. These details are complete. Publish the repository with its real local history. Do not claim peer review, owner approval or live measurements before they occur. A fresh Colab run of the older version does not verify the upgraded dependency/SDK/tool-loop version.

The earlier PDF also names explicit targets: safety 100%; paired guard ≥95%/0%; judge κ≥0.6; provider cached inputs ≥65%; dollar cost reduction ≥60%. The offline safety/guard checks pass. Live judge/cache/dollar targets remain unmeasured, not automatically satisfied by implementation.
