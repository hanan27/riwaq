# Riwaq benchmarks

The baseline section contains executed OFFLINE SDK SIMULATOR results, which test application code rather than model weights. Subsequent local-model or commercial sections, if present, contain separate executed evidence. Baseline token estimates never establish live quality, provider caching, dollar savings or GPU throughput.

| Step | Requests | Model calls | Estimated tokens | Dollar cost | Eval | Safety |
|---|---:|---:|---:|---|---:|---:|
| baseline | 100 | 100 | 26160 | Not measured | 100.0% | 100.0% |
| exact response cache | 100 | 20 | 5232 | Not measured | 100.0% | 100.0% |
| exact + lexical semantic cache | 100 | 18 | 4734 | Not measured | 100.0% | 100.0% |

Model-call reduction on the five-pass FAQ replay: 82.0%. This is a call-count reduction, not measured dollar savings. Near-miss wrong hits: 0/8. A lexical semantic tier is thresholded on a separate curated pair set; held-out near misses are compared with uncached pipeline answers. The small pair set needs owner review and is not an embedding benchmark.

| Extraction language | Cases | First-pass valid | Final valid | Correct slot/language |
|---|---:|---:|---:|---:|
| ar | 8 | 100.0% | 100.0% | 100.0% |
| en | 4 | 100.0% | 100.0% | 100.0% |

Guard block rate / false-positive rate: 100.0% / 0.0%.

Commercial/open-weight comparison: not run. Provider prompt-cache ratio: not measured (offline estimates cannot prove ≥65%). Self-host break-even: not measured. Use the live comparison cell and enter actual pricing and GPU hourly cost; compare hosting against both uncached and cached API traffic.
