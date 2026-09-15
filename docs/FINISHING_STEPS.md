# Finish Riwaq with a local Hugging Face model

Your earlier Colab run verified the application and SDK simulator. This version adds actual model inference in Colab, without a paid API or a Hugging Face token for the selected public model.

## 1. Run the latest notebook

Upload `Riwaq_Capstone.ipynb` to Colab. Choose **Runtime → Change runtime type → T4 GPU** (or a better GPU), then **Runtime → Run all**.

The first sections repeat the tested application checks. Section 12 automatically installs vLLM in a separate environment, downloads public Qwen weights, starts a server accessible only inside your runtime, and runs the same 84 golden cases through it. You do not need to edit model IDs, get an API key or enable a hidden switch.

Installation and GPU initialization may take several minutes. If the cell reports an error, preserve it and the log named in the error message. Do not replace the real-model results with simulator results. The small model may fail some quality cases; those failures must be inspected rather than removed from the golden set.

## 2. Save the results

At the end, the notebook downloads `Riwaq_results.zip` and `Riwaq_Human_Review.html`. Also choose **File → Download → Download .ipynb** to save the executed notebook. Return the ZIP and notebook. If browser downloads are blocked, find the files inside the printed temporary project folder in Colab's Files panel and download them there.

The ZIP contains reports, metrics, and setup/server diagnostics. It excludes API keys, environment files and human-label files. Model weights are not included.

## 3. Supply the required human review

Open `Riwaq_Human_Review.html` in your browser, or use the copy already in the project folder. It works without an internet connection.

- For each of 40 examples, read the reference and answer. Choose whether every factual claim is supported. A changed fee or invented extra requirement means “No”; a faithful paraphrase means “Yes.” All choices start blank.
- Confirm your reviewer name and download `owner_labels.json`.
- Expand the golden-set section, inspect the 84 expectations, and explicitly approve them if correct. Download `owner_approval.json`.

Return both files, or upload them into Colab's `/content` folder and rerun section 13 while the model is still running. The notebook checks that you did not accidentally review a different dataset. It computes actual judge agreement and Cohen's kappa and reports whether the judge qualifies. It does not manufacture your judgments.

## 4. Understand the remaining economic evidence

The notebook measures real local latency, throughput and returned prefix-cache counters. The cost table always includes evaluation verdicts. Missing cache counters remain unknown.

A free Colab session does not provide a commercial invoice or paid GPU hourly price. If you supply an hourly compute rate, costs are explicitly modeled from measured occupied time. Commercial break-even needs commercial per-request prices as well; both uncached and cached comparisons are supported, but no price is invented and no zero-denominator percentage saving is claimed.

## 5. Final rubric check and publication

The grading engine explicitly names both commercial and open-weight model runs. This workflow supplies the open-weight side. The instructor's statement that no real API is needed does not, by itself, specify what evidence replaces the commercial side. Keep that row pending unless actual evidence or an explicit acceptable alternative is supplied. Never rename a simulator or a second open-weight model “commercial.”

Once your actual results and human review are available, update the report from those files, resolve any safety/quality failures, and publish the repository with its genuine commit history. Your name, programme and cohort dates are already recorded. Repository publication and peer review cannot be claimed before they happen.

## Technical sources

The model comes from the [official Qwen model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct). vLLM documents [Linux/NVIDIA GPU requirements including T4](https://docs.vllm.ai/en/v0.18.2/getting_started/installation/gpu/), [Hermes tool parsing for Qwen2.5](https://docs.vllm.ai/en/v0.18.2/features/tool_calling/), and the [prefix-cache/usage server flags](https://docs.vllm.ai/en/v0.18.2/cli/serve/). The runtime is pinned; the exact downloaded model commit is resolved and recorded before serving. GPU installation is not locally verified on the development Mac.
