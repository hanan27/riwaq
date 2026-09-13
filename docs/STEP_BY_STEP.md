# Understand and present Riwaq, step by step

The delivered application works in offline demonstration mode. Its model is a deterministic simulator; real-model experiments are prepared but have not been run. Read this distinction before quoting any result.

## Step 1 — Understand the project idea

Riwaq helps students at a **fictional university** ask about admissions, course enrolment, official transcripts and advisor appointments. English and Arabic are supported. The source catalog says, for example, that a transcript costs **25 SAR**. This is fictional project data, not a claim about an actual university.

There are three main routes:

| Student message | Route | Result |
|---|---|---|
| “كم رسوم السجل الأكاديمي؟” | FAQ | Exact answer from the catalog, with source ID |
| “Book an advisor Monday 9” | Workflow | Extract a request, check trusted identity and consent, then book |
| “أحتاج موظف” | Escalation | Create a support handoff and stop |

A hostile request such as “reveal the system prompt” is refused before those routes run.

## Step 2 — Open and run the notebook

1. Go to Google Colab, select **File → Upload notebook**, and choose `Riwaq_Capstone.ipynb`.
2. Select **Runtime → Run all**.
3. The first cell unpacks the embedded source and datasets into a fresh temporary folder. No package, API key or external source file is needed.
4. Read each explanation before its code and inspect the printed output beneath the cell.
5. If a test fails, execution raises an error. Do not delete the assertion; inspect the failing case and fix the application.

The supplied notebook already contains actual output from a fresh local execution of its 19 code cells. That does not replace your final fresh **Colab** run. In Colab, choose **Runtime → Disconnect and delete runtime**, reconnect, and Run all again before submission.

## Step 3 — Understand what the model can and cannot decide

`LLMClient` is the model interface. The rest of the app asks it for a completion without importing a provider SDK. The offline `DemoClient` follows rules to exercise the app predictably. `HTTPClient` sends the same kind of request to a configured real endpoint.

`MeteredClient` wraps the adapter. It records prompt version, backend, request budget, retry attempt, token usage when supplied, and elapsed time. It retries one rate-limit failure and can try a configured fallback. If all backends fail, it returns a controlled unavailable response through the app.

The model can propose a slot. It cannot give itself permission, change the authenticated student, execute arbitrary Python, or create an unregistered tool.

**Defence answer:** “The model boundary lets me replace the provider while keeping the same validation, permissions, tools and evaluation.”

## Step 4 — Follow the five stages

1. **Input guard:** normalize Unicode and Arabic variants, then check instruction/privacy attack patterns. Oversized or invalid inputs are refused.
2. **Router:** choose FAQ, booking or human escalation using deterministic code.
3. **Context:** select a public catalog entry. Check that returned tool data matches the pinned source.
4. **Execution:** generate a bounded FAQ response or extract and process the booking request.
5. **Output guard:** reject internal markers, dangerous content, wrong source IDs or changed facts. An accepted FAQ must match the exact allowed source answer.

The notebook demonstrates each stage in its own code cell. This makes failures traceable: a wrong route differs from a bad extraction, which differs from an unauthorized action.

**Defence answer:** “I can inspect each stage independently, but my evaluation also runs the full integrated pipeline.”

## Step 5 — Understand the strict request schema

An appointment request has exactly three fields:

```json
{"service":"advising","slot":"mon-09","language":"en"}
```

- `service` is the allowed service enum, not any arbitrary string.
- `slot` is `mon-09`, `tue-11`, or null when unspecified.
- `language` is `ar` or `en`.

Additional fields such as `student_id` are rejected. A malformed answer triggers validation failure, one retry and then a versioned repair attempt. Three invalid attempts end the extraction safely. An unspecified slot asks for clarification.

The notebook deliberately feeds malformed JSON and wrong fields to prove the repair branch actually runs.

## Step 6 — Understand authentication and confirmation

A `Session` models trusted server state:

```python
Session('demo-student', ('student',), 'mon-09')
```

The student is authenticated, has the student role, and has explicitly confirmed the Monday slot. `session.authorize()` checks these facts at tool execution time.

This object is created in notebook code for demonstration. A real application must create it on a trusted server after login and confirmation. Typing “I am demo-student” into the chat does not create this session.

The booking tool writes to an in-memory dictionary. The same student repeating the same booking gets the same booking ID. Another student cannot overwrite the occupied slot. This is a real demonstration state change, but not a production database transaction.

**Defence answer:** “Authorization reads trusted session state, never an instruction from the model or user text.”

## Step 7 — Explain the tools and their risks

| Tool | Risk class | Protection |
|---|---|---|
| `lookup_service` | Read-only | Public pinned catalog only |
| `book_advisor` | Side-effecting | Session role, identity, confirmed slot, strict arguments, idempotency |
| `handoff` | Terminal | Records handoff and ends the route |

All tool calls log the tool name, risk class, iteration and outcome. Unknown tools, unexpected arguments and iteration numbers above three are denied. The application uses a bounded workflow rather than an open-ended autonomous agent.

## Step 8 — Read the guard results correctly

The development attack corpus has 32 messages, and the legitimate corpus has 32 messages. Both languages appear. Legitimate traps include harmless password questions and security vocabulary.

- **Block rate** = blocked attacks / all attacks.
- **False-positive rate** = blocked legitimate requests / all legitimate requests.

The executed offline guard run reports **32/32 attacks blocked** and **0/32 legitimate requests blocked**. These facts apply to this particular test corpus. They do not prove every possible attack is blocked.

The indirect-injection extension replaces tool results with five poisoned payloads. They are caught before model execution. Other tests inject malicious or factually incorrect generated answers and verify the output wall refuses them.

## Step 9 — Read the evaluation report

The golden set contains 84 cases: 48 Arabic and 36 English, including 40 safety cases. Each marginal intent, language, risk and difficulty category has at least eight cases.

The harness calls `CampusApp.respond`, exactly like the chat demonstration. It checks exact facts and source IDs for FAQ, owned state changes for bookings, terminal state for handoffs, and fixed refusals plus no side effects for safety.

The offline run passed **84/84**, including **40/40 safety**. This is useful application evidence. It is not a real LLM accuracy score because the simulator is intentionally deterministic.

Before submission, read every expectation. Generated fields say `owner_approved=False` because your review cannot be fabricated. Record approval separately; do not edit expectations just because the code failed.

## Step 10 — Explain the regression gate

A good average can hide a serious Arabic quality drop. Therefore, `regression_gate` compares each slice, not only the overall score.

The test prompt `faq.v2-bad` replaces 25 with 250 in Arabic transcript answers. The output guard refuses those incorrect answers. Safety remains protected, but the FAQ/Arabic quality slices fall because a correct answer was expected. The gate rejects the candidate.

**Defence answer:** “The gate is useful because I have shown it allow a clean run and reject a seeded regression.”

## Step 11 — Explain caching and costs honestly

The cost experiment replays 20 FAQ questions five times, for 100 requests:

- No cache makes 100 simulator calls.
- Exact response caching makes 20 calls.
- Exact plus the calibrated lexical tier makes 18 calls in the current replay.

The final reduction is **82% of model calls**. Token counts in offline mode are estimates. This is not proof of an 82% dollar saving.

Cache keys contain answer-changing information: query, language, source contents, catalog version, prompt version, backend and guard version. Only public answers are cached. Every cached answer still passes the output guard.

The lexical similarity tier is calibrated on 12 separate pairs. Eight held-out near-miss pairs produce zero wrong cached answers compared with fresh pipeline results. The pair set is small and needs independent review; do not call it a universal semantic-search benchmark.

Real provider prompt caching is a different mechanism. Its evidence must come from `usage.cached_input_tokens` as translated from the provider response. The rubric's ≥65% cached-input target and ≥60% dollar-saving target remain unmeasured.

## Step 12 — Run real backends when access is available

Use a commercial endpoint and an endpoint serving open-weight model weights. Store credentials privately. The final notebook cells document all `RIWAQ_COMMERCIAL_*` and `RIWAQ_OPEN_WEIGHT_*` configuration variables.

Set `RUN_LIVE=True` only when both endpoints are ready. The runner evaluates both on the same golden set, prints quality slices, and records latency and provider usage. Set verified prices to obtain dollar estimates; unknown prices remain unknown. Never paste a key into a notebook cell or a commit.

The exact-source FAQ policy is intentionally strict, so a model that paraphrases facts may be safely refused. If live scores are poor, inspect output formats and prompt behavior. Revise prompts with a **new version**, rerun the original cases, and preserve the record.

## Step 13 — Calibrate the judge independently

The notebook creates 40 candidate reference/answer pairs. It leaves their human labels blank.

1. Read each reference and answer yourself.
2. Set `supported` to true or false and mark `owner_approved` only after review.
3. Save the reviewed file privately as `owner_labels.json` in the runtime folder.
4. Enable the live judge cell.
5. Inspect Cohen's κ and the confusion matrix. The target is κ ≥0.6.

Kappa measures agreement beyond chance. Running a perfect synthetic example only checks the formula; it does not qualify a real judge. Safety remains deterministic even after a judge qualifies.

## Step 14 — Explain hosting economics

Measure requests per second on an actual self-hosted model. Supply actual GPU hourly cost and verified API request costs.

```text
break-even requests/hour = hosting dollars/hour ÷ API dollars/request
usable capacity/hour = measured requests/second × 3600 × utilization
```

Compare hosting against **both** uncached API traffic and response-cached API traffic. A GPU may look cheaper than an unoptimized API and still be more expensive than the cached application. The code computes both comparisons; no measured hosting recommendation is claimed yet.

## Step 15 — Prepare the final submission

Read `docs/CRITERIA_AUDIT.md` line by line. Add your full name and actual cohort dates to the README, review labels, complete live evidence, and rerun Colab fresh. Publish this project directory as its own repository with the existing local commit history. Do not publish secret files or invent peer signatures.

The local repository already records real development checkpoints. Its auto-detected Git committer identity is not a substitute for your required full name in the README. Set your preferred Git identity before adding future commits.

Submit the notebook, evaluation report, benchmarks, decisions, technical guide and repository URL. Be clear about any requirement still unmet. No distinction or passing grade is guaranteed by an offline green run.

## Short practice questions

1. Why is the authenticated student ID absent from the extracted request?
2. What happens if the model returns an extra JSON field?
3. How does the code prove fallback actually ran?
4. Why does the degraded prompt fail quality even when safety is green?
5. What separates response-cache hits from provider prompt-cache tokens?
6. Why are 84 simulator passes insufficient evidence for choosing a live model?
7. Which remaining results require your independent judgment or access?
