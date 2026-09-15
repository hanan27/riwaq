# Riwaq decisions record

Offline evidence comes from a deterministic simulator, not model weights. Live model selection remains conditional on measured results.

## ADR 001 — Router-first campus workflow

Track B serves a fictional Namaa University. A deterministic router selects a single-call public FAQ, a bounded advising workflow, or a terminal support handoff. This keeps the small factual domain inspectable and makes authorization independent of model behavior. Every generated completion passes through `MeteredClient` and an `LLMClient` adapter. The notebook has five independently demonstrated stages. No real university rules or student data are used.

## ADR 002 — Provider boundary and fault handling

Use an OpenAI-compatible HTTP contract for separately configured commercial and open-weight endpoints. No specific model wins before evaluation. Provider JSON mode helps formatting, but local enum validation still decides validity. Retry one rate-limit error; switch to a configured fallback on an outage; return a bilingual unavailable response if exhausted. Do not silently call the simulator when a live provider fails. Output is capped at 256 tokens for FAQ and 160 for extraction. HTTP requests time out after 15 seconds; the retry budget bounds total attempts. Provider authentication errors are surfaced as unavailable without revealing response bodies or credentials.

## ADR 003 — Exact grounding and the reversed trade-off

The initial architecture consideration was a free-form friendly FAQ answer checked only for dangerous strings. During implementation this was replaced by exact source matching before an answer is served: an innocuous-looking invented fee would otherwise pass the output wall. This narrows paraphrasing and coverage, but makes the protected facts deterministic. The intentionally degraded Arabic fee prompt is refused and the regression gate rejects the quality drop. This records an implementation decision, not an invented historical deployment experiment.

## ADR 004 — Authorization and privacy

Identity, role and confirmed slot come only from trusted `Session` state. Model output cannot add an identity field to the strict appointment schema. The tool registry rejects extra arguments, missing consent, wrong roles, excessive iterations, and occupied slots. Repeating the same booking is idempotent. This notebook is a single-process demonstration; production would require an authenticated server, expiring consent, database uniqueness constraints, transactional writes and audit retention policy.

## ADR 005 — Cost and routing recommendation

Exact response caching is restricted to public FAQ results and is checked again by the outbound wall. Keys include the exact query, language, source contents, catalog version, prompt version, backend and guard version. Actions are never cached. An optional lexical similarity tier uses a threshold measured on a separate 12-pair set and is checked against held-out near misses; its small calibration set requires independent review. The deterministic router and guards have zero model calls, rather than hidden unmetered calls. Offline call-count savings do not establish dollar savings. Both live backends must run on the same frozen golden set before choosing a production route. Compare quality by language, intent, risk and difficulty, then cost and latency. Host only if measured capacity at the chosen utilization exceeds the break-even demand **against both uncached and cached API traffic**; otherwise keep hosted inference. Pricing and GPU throughput cannot be inferred from this laptop's simulator.

## ADR 006 — Evaluation ownership

The generated golden set is reviewable and reproducible from immutable input seeds. Automated expected labels are not human approval. The owner must inspect expectations and judge-label candidates before approving them. A calibrated judge may supply supplementary quality evidence; deterministic code alone carries safety claims. No grade is asserted by this project.

## ADR 007 — Grading-engine implementation upgrade, 15 September 2026

The detailed grading-engine rubric requires Pydantic validators, strict schema generation, SDK invocation, actual function-call round trips, file prompts, Saudi PII masking and a committed baseline. The original dataclass/manual workflow/inline registry did not establish those requirements. Replace them while preserving the original 84 expectations and returned Colab evidence.

Use the OpenAI Python SDK inside the existing typed adapter. The default run invokes that SDK against an explicit HTTPX mock transport and a deterministic model simulator. This makes wire contracts and SDK use testable without an API key; it does **not** turn simulator quality, estimated tokens or synthetic usage into live-model evidence. Live adapters use the same SDK path with configured model IDs and endpoints. No silent fallback to simulation is permitted during live experiments.

Pydantic models generate strict JSON schemas and still validate locally. Tool definitions are strict; the loop validates arguments and authorizes before mutation, returns tool results to the model, limits rounds, and stops on terminal handoff. A booking receipt remains valid if the final model acknowledgement fails, because the action has already happened.

Prompts are loaded from versioned files with changelogs. Stable system instructions come first; request-dependent masked data and tool results come last. Never add timestamps or identities to the prefix. The meter records the prompt content hash. Provider prompt-cache counters are recorded only when present; a missing counter is unknown. This small domain may not produce long enough prompts to meet a provider's caching threshold, so ≥65% must be tested, not presumed.

Saudi PII detection is conservative and format-based. Mask ID/iqama numbers, local/international phone formats, IBAN and email before model access, exception feedback and logs. Reject detected PII outbound. This is not comprehensive entity recognition: arbitrary names, addresses and novel obfuscations need broader coverage.

The versioned golden set and frozen baseline are data files. Normal execution verifies provenance and compares candidates; it never rewrites the expectations or promotes the baseline. Update either only as a deliberate reviewable change. Judge calibration requires independent human labels and reviewer/date provenance; the known label count or a synthetic formula test is not calibration evidence.
