# Riwaq design decisions

## Configuration and execution

`configs/models.json` is the single source of truth for runtime model IDs, HF routes and pricing assumptions. Notebook setup clones/uses the actual repository and verifies the imported source path. The notebook builder writes orchestration cells, not a second copy of application files. Historical raw results describe their original configuration only.

## Existing Hugging Face architecture

Keep the typed `LLMClient` boundary, metering, retries/fallback and Hugging Face hosted adapter through the existing compatible SDK. Local weights run directly in Transformers. No additional model provider or server is introduced. The default interactive demonstration uses the existing offline SDK simulator without credentials; real model evaluation is optional and explicitly labelled. Missing `HF_TOKEN` skips hosted evaluation before model requests.

## Authorization and prompts

`CampusApp.respond` calls five named stages: `stage_input`, `stage_route`, `stage_context`, `stage_execute`, and `stage_output`. The notebook demonstrates those production functions. Versioned prompt text loads from `prompts/`; metering retains prompt IDs/hashes.

Booking tools enforce authenticated fictional session identity, student role and exact slot consent in Python before mutation. The tool loop also prevents the model from changing the extracted slot. R079 is tested through the production application and SDK mock; golden expectations remain unchanged. This deterministic proof does not claim a new real-model run.

## Evaluation and economics

Preserve the frozen golden set and regression baseline. Safety assertions run independently of the judge. Invalid/null predictions yield NOT COMPLETED with no agreement/kappa; valid paired reference labels may yield reference agreement, but human calibration requires independent reviewer, approval and date. Never infer human review from generated fixtures.

Response caching remains limited to public FAQs with content/model/prompt/guard identity keys and outbound rechecks. Provider prompt caching is separate: missing usage is unknown, and zero cached tokens establish no savings. Costs based on catalog rates or hardware-hour assumptions are estimates, not invoices. Break-even requires successful local throughput and available hosted cost measurements. Historical results remain unchanged as provenance, not current evidence.
