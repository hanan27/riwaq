# Hugging Face workflow verification

The newest notebook completed **23 code cells locally**, with **33 unit/contract/orchestration tests passing** and the original **84/84 simulator-backed golden cases**, including **40/40 safety**, still green. The human-review page JavaScript passed a syntax check. Candidate integrity, owner-approval hashes, export allowlisting, unknown-cost handling, loopback-only server flags and failure-before-download on unsupported hosts are tested.

**This is not a GPU inference result.** The development machine is macOS/x86_64 without the required Linux/NVIDIA runtime. The notebook explicitly reports that local model inference was not run in this process. vLLM installation, Qwen weight loading, model quality, actual prefix-cache counts and actual GPU throughput need the new Colab run. No human label, commercial result, hourly price or kappa has been invented.

The earlier user-returned 21-cell Colab run is preserved in `evidence/notebooks/colab_before_huggingface.ipynb`. The old deleted root results file was not recreated. The golden dataset and baseline were not changed.

Reproduce code verification with the pinned project environment:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_notebook.py
python3 scripts/execute_notebook.py
```

For the actual model experiment, use Colab GPU and follow `docs/FINISHING_STEPS.md`. Return the executed notebook and `Riwaq_results.zip`; the review form produces human-label and golden-approval files separately.
