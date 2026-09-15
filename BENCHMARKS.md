# Riwaq benchmarks

## Historical measurements only

Source: unchanged `run-results.json`, run UTC 2026-09-15T11:31:25.065420+00:00. These measurements describe the earlier code/configuration, not the corrected notebook. Current model IDs come only from `configs/models.json`.

| Backend | Optimization step | Requests | Mean latency ms (measured) | USD | Quality verdict | Provider prompt cache |
|---|---|---:|---:|---|---|---|
| hosted | no cache | 40 | 92.85 | Unavailable | 0.0% exact FAQ success; regression gate FAILED | Not observed |
| hosted | response cache | 40 | 86.83 | Unavailable | 0.0% exact FAQ success; regression gate FAILED | Not observed |
| open_weight | no cache | 40 | 1618.66 | 0.017985 (modeled at assumed $1/hour) | 5.0% exact FAQ success; regression gate FAILED | Not observed |
| open_weight | response cache | 40 | 1645.13 | 0.018279 (modeled at assumed $1/hour) | 5.0% exact FAQ success; regression gate FAILED | Not observed |

Hosted timings include failed attempts, so they are not successful-inference latency benchmarks. Response-cache quality preservation alone does not override a failed regression gate.

## Current evidence requirements

- No new model benchmarks were run for this revision.
- Response caching is implemented for public FAQs only. Its deterministic test verifies fewer model calls with preserved simulator quality; this establishes no hosted savings.
- Provider prompt caching is distinct: absent `cached_input_tokens` is unavailable; an observed zero establishes no savings. Only actual positive cached usage can support a savings claim, and unknown cached pricing prevents a dollar estimate.
- Hosted dollar costs are unavailable in the historical run. Configured catalog prices are historical estimates, not current quotes or invoices.
- Historical local throughput is warmed serial FAQ workload throughput, not saturated GPU capacity.
- Measured break-even is unavailable. A new comparison needs successful measured local throughput and usable hosted per-request cost before calculating it.
- Judge calibration is NOT COMPLETED; failed/null predictions do not yield valid Cohen’s kappa.
