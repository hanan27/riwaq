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

Exact response caching is restricted to public FAQ results and is checked again by the outbound wall. Keys include the exact query, language, source contents, catalog version, prompt version, backend and guard version. Actions are never cached. The deterministic router and guards have zero model calls, rather than hidden unmetered calls. Offline call-count savings do not establish dollar savings. Both live backends must run on the same frozen golden set before choosing a production route. Compare quality by language, intent, risk and difficulty, then cost and latency. Host only if measured capacity at the chosen utilization exceeds the break-even demand **against both uncached and cached API traffic**; otherwise keep hosted inference. Pricing and GPU throughput cannot be inferred from this laptop's simulator.

## ADR 006 — Evaluation ownership

The generated golden set is reviewable and reproducible from immutable input seeds. Automated expected labels are not human approval. The owner must inspect expectations and judge-label candidates before approving them. A calibrated judge may supply supplementary quality evidence; deterministic code alone carries safety claims. No grade is asserted by this project.
