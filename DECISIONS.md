# Decisions — submitted Riwaq run

This retrospective record describes the implementation executed in `Riwaq_Capstone.ipynb` on 2026-09-15. It records design rationale; it does not claim a new run.

## 1. One typed model boundary

Use `LLMClient(Protocol)` for model access and `MeteredClient` for retry, bounded backoff, fallback and accounting. The application depends on this contract; provider SDK calls remain in the adapter. This keeps the same application and golden set usable with hosted inference and local weights without introducing a service layer.

## 2. Hosted SDK and direct local weights

The submitted configuration uses the OpenAI Python SDK at `https://router.huggingface.co/v1`, authenticated with `HF_TOKEN`. Its primary alias resolves to `openai/gpt-oss-20b:deepinfra`; its fallback resolves to `openai/gpt-oss-20b:together`. The submitted configuration records schema/tool capability declarations and catalog rates. These declarations are not successful inference evidence: all hosted evaluation requests failed in this run.

The local alias resolves to `Qwen/Qwen2.5-1.5B-Instruct`, loaded directly with Transformers. The small model limits download and GPU memory requirements. The measured run used a Tesla T4 and resolved revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Its low FAQ accuracy is an observed trade-off, not a reason to relax the frozen expectations. There is no local model server or container.

## 3. Contracts and authorization

Use strict Pydantic contracts, API JSON-schema requests, and a bounded extraction validate/retry/repair sequence. Tool names and argument schemas are allowlisted. Booking requires a trusted session, student role and confirmed slot; the model cannot grant authorization. The submitted run nevertheless fails the intended slot-consent invariant on R079. That failure remains unresolved and blocks acceptance.

## 4. Prompt and cache discipline

Load instructions from versioned files. Place stable instructions first, then masked request data and tool history. This preserves a reusable prompt prefix without assuming a provider cache hit. Use an exact response cache for public FAQs only; keys include text, language, source content/version, prompt version/hash, model identity and guard version. Recheck cached responses through the outbound wall; never cache bookings.

## 5. Evidence and economics

Keep the same versioned golden set and committed regression baseline for both backends. Deterministic assertions carry safety claims; the single-dimension judge measures factual support only. Human calibration is pending, all judge calls failed, and the printed kappa is not valid calibration evidence. Both regression gates reject this run.

Read usage and latency from actual requests. Unknown hosted costs and cache counts remain unknown. Local compute cost is modeled using the explicit $1/hour assumption, not a bill. Throughput is warmed serial FAQ throughput, not saturated GPU capacity. No measured hosted break-even can be claimed without a successful hosted cost measurement.

## Submission provenance

The submitted notebook's embedded configuration and source are authoritative for this run. The root configuration may describe an earlier model choice. Documentation added after execution does not change saved code, outputs, labels, baseline or raw measurements.
