# Riwaq evaluation report

These are executed OFFLINE SIMULATOR results. They test application code, not a commercial or open-weight model. No live quality, provider cached-token, dollar-saving or GPU-throughput claim is made.

| Slice | Cases | Passed | Rate |
|---|---:|---:|---:|
| difficulty=easy | 22 | 22 | 100.0% |
| difficulty=hard | 62 | 62 | 100.0% |
| intent=escalation | 12 | 12 | 100.0% |
| intent=faq | 20 | 20 | 100.0% |
| intent=safety | 40 | 40 | 100.0% |
| intent=workflow | 12 | 12 | 100.0% |
| language=ar | 48 | 48 | 100.0% |
| language=en | 36 | 36 | 100.0% |
| overall | 84 | 84 | 100.0% |
| risk=action | 12 | 12 | 100.0% |
| risk=public | 32 | 32 | 100.0% |
| risk=safety | 40 | 40 | 100.0% |

Guard attack block rate: 100.0% (32 cases). Legitimate false positives: 0.0% (32 cases).

Clean gate: `{'allowed': True, 'failed_slices': []}`. Seeded prompt regression: `{'allowed': False, 'failed_slices': ['difficulty=easy', 'difficulty=hard', 'intent=faq', 'language=ar', 'overall', 'risk=public']}`. The output wall refuses incorrect fees; the quality slice still falls, so the gate blocks it.

## Provenance and limitations

Golden-set SHA-256: `885aceead8b48720de86cdfe877cf0f19ea9df4017847378e41d9c8a887c03f2`. Expectations are generated from versioned seeds and await owner review. Strata are marginal categories, not every Cartesian intersection. Safety is oversampled; production prevalence is unknown.

No live backends have been run. Judge calibration is pending and no judge gates safety or releases. Rule-based routing and attack detection are limited to tested language patterns; held-out attacks may evade them. Exact-copy answers intentionally limit conversational flexibility. In-memory bookings demonstrate authorization and idempotency but are not a concurrent production booking database. Session objects represent trusted server state; real authentication and a durable confirmation UI are outside this notebook.

Fresh execution was checked by running every code cell in a new Python process, with embedded source and data only. A Google Colab browser execution and peer review remain unverified.
