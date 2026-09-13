# Criterion-by-criterion audit

Checked against the supplied **Capstone — your own LLM application – LLM Application Engineering.pdf**, all eight PDF pages (printed page labels 1–9). The local course `capstone.qmd` was also inspected. Status describes evidence, not a predicted grade.

| Criterion | Weight | Implemented / executed evidence | Still needed for full evidence |
|---|---:|---|---|
| Architecture and model boundary | 15 | Original Track B; router; boundary AST assertion; config-selected adapters; rate-limit, outage and exhaustion transcripts; ADR | Run one commercial and one open-weight backend live |
| Structure and tools | 15 | Exact schema and enums; validate/retry/repair drill; Arabic/English extraction rates; three tool risks; session authorization; terminal handoff; bounded workflow; tool logs and negative tests | Measure live-model extraction, review domain corpus coverage |
| Prompts and guardrails | 15 | Versioned prompt registry with changelogs; five stage cells; 32 attacks + 32 legitimate cases with traps; paired rates; normalized Arabic/Unicode; fixed bilingual refusals | Held-out coverage and peer red-team evidence |
| Evaluation | 20 | 84 original cases; 48 Arabic; 40 safety; every marginal category ≥8; real pipeline; 100% local safety; clean and failing regression gates; generated report | Owner approval of expectations; independent labels and live judge κ≥0.6; live backend runs |
| Cost/latency | 15 | Every model attempt metered; exact-cache isolation; measured lexical similarity threshold; eight near misses; executed before/after with eval beside every row | Provider cached-input ratio ≥65%; real ≥60% dollar savings; broader independent semantic-cache review |
| Comparison/recommendation | 10 | Live-run entry points; sliced metrics; break-even function; conditional routing ADR | Both live golden runs; measured self-host throughput; cost comparisons against both uncached and cached API |
| Complete application | 10 | Self-contained notebook; four-part bilingual demo; fresh-process execution with outputs | Fresh Colab browser Run all; final identity/cohort metadata; repository URL and publication of the existing local incremental history |
| Extension | up to +5 | Five actual poisoned tool-result cases, five poisoned output cases and negative tool tests | Extension points only apply if mandatory scope scores ≥80; do not assume them |

## Absolute pass rule

The safety suite must be green at submission. This is stronger than an average quality score. The notebook asserts safety is 100% and stops on failure. A local green suite does not promise the hidden suite passes.

## Four grading caps explicitly checked

- Golden expectations are generated from seeds, with a hash in the report. They are not edited to conceal failures.
- Attack block rate and legitimate false-positive rate are always presented together.
- Each cache benchmark row includes the evaluation and safety verdict.
- An uncalibrated judge never gates a release. Calibration is reported as pending rather than fabricated.

## Non-code requirements

The README must contain the trainee's full name and programme cohort dates before submission. These details have not been supplied. No peer architecture signature or peer attack session has been claimed. A public/private GitHub repository URL has not been created. Local history must be uploaded intact, using the owner's account; fabricated backdated history is not acceptable. Review the course's own rules for assisted work and acknowledge assistance appropriately.
