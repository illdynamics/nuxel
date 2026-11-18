# SONARBIRD — MiniLM-L6 Routing Implementation Mission

**Project:** Nuxel / PenGuru Squad  
**Target device:** Samsung Galaxy S10+ / Exynos9820 / ARM64  
**Target model:** `sentence-transformers/all-MiniLM-L6-v2`  
**Preferred runtime:** ONNX Runtime CPU  
**Preferred optimized format:** INT8 ARM64, subject to validation  
**Primary objective:** Intelligent, accurate, offline routing between ChatBird, CodeBird and the Nuxel System Supervisor.

---

# 1. Mission

You are the lead AI inference, machine-learning, ARM64 optimization and Nuxel integration engineer.

Your task is to transform SonarBird into a genuinely functional, lightweight intent-routing subsystem for PenGuru Squad.

CodeBird has already been confirmed generating real responses on the physical S10+. Preserve that working functionality.

SonarBird currently has no installed routing model, according to the latest owner report.

We have selected:

**`sentence-transformers/all-MiniLM-L6-v2`**

Your mission is to acquire, adapt, train, optimize, test and integrate this exact model into Nuxel.

Do not replace the model with a generative LLM. SonarBird must be a compact classifier, not a second conversational model.

Complete all safe engineering work possible, including model preparation, classification training, ONNX conversion, integration, tests, optimization and documentation.

Do not declare completion until genuine requests are routed correctly on the S10+.

# 2. Target Architecture

PenGuru must implement the following logical flow:

```text
                USER REQUEST
                     |
                     v
              PENGURU SQUAD
                     |
                     v
           Input normalization
           and explicit mode check
                     |
                     v
                 SONARBIRD
          all-MiniLM-L6-v2
                     |
              384-D embedding
                     |
              Trained classifier
                     |
           Confidence / OOD gate
                     |
           +---------+---------+
           |         |         |
          CHAT      CODE     SYSTEM
           |         |         |
           v         v         v
       ChatBird   CodeBird  Supervisor
                               |
                          Permission
                            broker
                               |
                       Authorized API
```

The classifier must not directly execute commands.

SonarBird only recommends routing. A separate component is responsible for permissions and system actions.

# 3. First Audit the Actual Repository

Working directory:

`/Users/wicked/x/nuxel`

Before implementing anything:

1. Inspect the current Git branch, HEAD and working tree.
2. Read all PenGuru Squad documentation and implementation phases.
3. Locate the actual SonarBird source, service definitions, model manifest, router API and configuration.
4. Identify the existing ChatBird and CodeBird integration APIs.
5. Find the Model Store and existing package-signature verification mechanisms.
6. Inspect permission and Supervisor integration.
7. Identify existing resource-management, thermal and battery-saving policies.
8. Check the ARM64 target toolchain and currently installed inference runtimes.
9. Preserve all unrelated development and existing working functionality.

Do not invent new repository paths when an existing module already implements the required abstraction.

Prefer extending the current SonarBird implementation over replacing it.

Record a baseline before changing code.

# 4. Understand the Exact Model

Model source:

https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

Properties:

| Property | Value |
|---|---|
| Architecture | MiniLM encoder |
| Parameter count | Approximately 22.7 million |
| Embedding dimension | 384 |
| Layers | 6 |
| Model purpose | Sentence embeddings |
| Primary language | English |
| License | Apache 2.0 |
| Default maximum input | 256 WordPiece tokens |
| Inference type | Encoder, not text generation |

The exact model is an embedding encoder.

It does NOT output `CHAT`, `CODE` or `SYSTEM` labels automatically.

You must implement a task-specific classifier on top of its embeddings.

## Critical design decision

Start with the pretrained encoder **frozen**.

Do not immediately fine-tune all 22.7 million parameters.

Instead:

1. Extract normalized embeddings.
2. Train a lightweight classifier.
3. Evaluate routing accuracy.
4. Calibrate confidence and uncertainty handling.
5. Optimize the encoder for ARM64.
6. Fine-tune the encoder only if the simpler solution demonstrably fails.

This keeps training inexpensive, preserves the original embedding quality and avoids an unnecessary large model-training process.

# 5. Acquire the Model Correctly

Use the official Hugging Face repository.

Pin an exact, immutable model revision or commit.

Do not depend on the moving `main` branch in production.

Prepare a host-side Python virtual environment containing the required model preparation packages.

Suggested dependencies:

```bash
python3 -m venv .venv-sonarbird

source .venv-sonarbird/bin/activate

python -m pip install \
  sentence-transformers \
  "sentence-transformers[onnx]" \
  optimum-onnx \
  onnxruntime \
  scikit-learn \
  numpy \
  huggingface-hub
```

Resolve and lock actual compatible dependency versions after validation.

Download the exact model snapshot using Hugging Face's official tooling.

Preserve:

- Model weights.
- Tokenizer files.
- Model configuration.
- Sentence Transformers pooling configuration.
- License information.
- Source revision.
- SHA-256 hashes.

Keep downloaded weights outside Git.

Do not enable remote model code execution unless a separately verified requirement exists. This model should not require it.

Store all model artifacts through Nuxel's existing Model Store, including integrity metadata.

# 6. Define SonarBird's Routing Contract

Implement the following primary routes.

## CHAT

Use ChatBird for conversational and explanatory requests.

Examples:

- "Hello, how are you?"
- "Explain how neural networks work."
- "Summarize this paragraph."
- "What does airplane mode do?"
- "Help me understand this error message."
- "Tell me about the Exynos9820."

CHAT must not silently trigger privileged actions.

## CODE

Use CodeBird for software-development tasks.

Examples:

- "Write a Python function."
- "Fix this JavaScript bug."
- "Explain this compiler error."
- "Refactor my Bash script."
- "Generate unit tests for this module."
- "Why is this Rust code failing?"
- "Review this Git diff."

Requests asking for code that interacts with the operating system still belong in CODE when the user is asking for code generation rather than immediate execution.

CodeBird output must never execute automatically.

## SYSTEM

Use the Supervisor path for explicit requests to act on Nuxel.

Examples:

- "Turn off Wi-Fi."
- "Lower my screen brightness."
- "Enable Bluetooth."
- "Show the current battery state."
- "Open the device settings."
- "Enable battery saver."

SYSTEM is a routing suggestion, **not authorization**.

All actions must go through the typed, permission-enforcing Nuxel Supervisor.

Do not let the model itself issue shell commands, write privileged files, or invoke arbitrary services.

## AMBIGUOUS / UNKNOWN

Support an internal abstention result when the classifier is unsure.

For example:

- "Can you handle this?"
- "Do something with my network."
- "Fix everything."
- A request containing several conflicting intentions.
- Out-of-distribution inputs.
- Inputs in an unsupported language.

Fallback to a safe conversational response or ask for clarification.

Do not guess a privileged action.

# 7. Build a High-Quality Training Dataset

Create a versioned, reviewed routing dataset.

Use JSONL or the existing repository dataset format.

Recommended record structure:

```json
{
  "text": "Write a Python function to sort a list.",
  "label": "CODE",
  "group": "python_generation",
  "language": "en"
}
```

Start with several hundred diverse examples per major route, then expand based on observed errors.

Create independent groups for:

- Normal examples.
- Paraphrases.
- Short inputs.
- Long inputs.
- Technical jargon.
- Informal language.
- Mixed intent.
- Negated requests.
- Quoted commands.
- Code blocks.
- Ambiguous requests.
- Out-of-distribution text.
- Untrusted copied content.
- Unsupported languages.

Avoid a dataset dominated by obvious keywords.

For example, this is important:

```text
"Tell me what Wi-Fi does."       -> CHAT

"Write a Wi-Fi diagnostic."     -> CODE

"Disable Wi-Fi now."            -> SYSTEM

"Explain how to disable Wi-Fi." -> CHAT
```

The word "Wi-Fi" must not automatically produce SYSTEM.

Likewise, the word "Python" does not always imply CODE.

The classifier must learn **the intended task**, not simply recognize keywords.

## Training data privacy

Do not automatically harvest private conversations.

Use authored examples, reviewed test cases and explicitly consented data.

Do not upload user conversations or secrets to a cloud training service.

## Dataset splitting

Use:

- Training split.
- Validation split.
- Independent held-out test split.

Separate paraphrase families and near-duplicate examples across splits to prevent data leakage.

Include hard negative examples in the final test.

Document dataset provenance, label definitions and class balance.

# 8. Train the Routing Classifier

Implement and compare at least two approaches.

## Baseline A — Semantic prototypes

For each route, create a representative set of labeled examples.

Encode them with MiniLM.

Normalize the embeddings.

Calculate class prototypes or use nearest-neighbor similarity against labeled examples.

Compare the incoming request embedding with these references.

This is useful as a simple, interpretable baseline.

However, raw cosine similarity is not inherently a calibrated classification probability.

## Baseline B — Trained classification head

Train a small classifier using the frozen MiniLM embeddings.

Preferred first implementation:

**Multiclass logistic regression over 384-dimensional normalized embeddings.**

This creates a very small routing head.

The encoder supplies semantic features.

The classifier learns the boundaries between CHAT, CODE and SYSTEM.

Example reference training logic:

```python
import json
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# Load reviewed training records.
records = [
    json.loads(line)
    for line in open("train.jsonl", encoding="utf-8")
    if line.strip()
]

texts = [r["text"] for r in records]
labels = [r["label"] for r in records]

X = model.encode(
    texts,
    normalize_embeddings=True,
    convert_to_numpy=True,
)

classifier = LogisticRegression(
    class_weight="balanced",
    max_iter=2000,
    random_state=42,
)

classifier.fit(X, labels)

artifact = {
    "classes": classifier.classes_.tolist(),
    "weights": classifier.coef_.tolist(),
    "bias": classifier.intercept_.tolist(),
    "embedding_dimension": int(X.shape[1]),
    "normalization": "l2",
}

with open("sonarbird-head.json", "w") as f:
    json.dump(artifact, f, indent=2)
```

This is a starting example, not the complete production training pipeline.

Implement proper train/validation/test separation, version pinning, dataset hashes, calibration and evaluation.

Do not train and evaluate on the same data.

## Runtime inference

For an input embedding `x`, compute the classifier logits:

```text
logits = W × x + b
```

Apply the appropriate classification decision logic.

If using softmax, treat its scores as uncalibrated until evaluated and calibrated.

Use validation data to establish a confidence and abstention policy.

Store the small classifier weights separately from the encoder model.

This allows updating routing behavior without rebuilding the entire MiniLM encoder.

# 9. Confidence, Ambiguity and Safety

Implement a robust decision layer.

Evaluate:

- Highest class score.
- Difference between first and second class.
- Calibrated confidence, if available.
- Distance or similarity to known training examples.
- Explicit user-selected mode.
- Whether the request is ambiguous.
- Whether a request contains untrusted quoted instructions.

Do not assume the largest softmax output is always trustworthy.

A three-class classifier may confidently misclassify an input completely unlike its training examples.

Build an out-of-distribution fallback.

Determine thresholds empirically using the validation set, and retain them in the versioned classifier manifest.

Do not hardcode guessed confidence thresholds and call them calibrated.

## Routing precedence

Use this order:

1. Explicit user-selected PenGuru mode.
2. Strongly typed UI actions and existing trusted application context.
3. Deterministic, well-tested routing rules where appropriate.
4. SonarBird semantic classifier.
5. Confidence and ambiguity policy.
6. Safe fallback.

An explicit CODE mode must not silently switch to SYSTEM because of the model's prediction.

A SYSTEM route must still pass every permission and authorization check.

Instructions inside quoted documents, pasted source code and retrieved text must not grant permissions or change routing authority.

# 10. Export MiniLM to ONNX

Use Sentence Transformers' supported ONNX backend.

Official guide:

https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html

Example:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2",
    backend="onnx",
)

model.save_pretrained("sonarbird-onnx")
```

Inspect the actual exported files and runtime dependencies.

Verify the ONNX graph inputs and outputs.

## Critical pooling requirement

The raw ONNX transformer generally outputs token embeddings.

It does not automatically provide the complete Sentence Transformers sentence-embedding pipeline when used directly through ONNX Runtime.

Reimplement or integrate:

1. Exact tokenizer.
2. Token IDs.
3. Attention mask.
4. Correct maximum sequence length.
5. Attention-mask-aware mean pooling.
6. L2 normalization.
7. 384-dimensional output validation.

Reference pooling logic:

```python
masked = token_embeddings * attention_mask[..., None]

pooled = masked.sum(axis=1) / np.maximum(
    attention_mask.sum(axis=1, keepdims=True),
    1e-9,
)

normalized = pooled / np.maximum(
    np.linalg.norm(pooled, axis=1, keepdims=True),
    1e-12,
)
```

Match the source model's actual pooling and normalization configuration.

Padding tokens must not affect the result.

The ONNX sentence embeddings must be compared against the original Sentence Transformers embeddings on the same inputs.

Do not claim parity merely because dimensions match.

# 11. Create an ARM64 INT8 Candidate

Use the official ARM64 dynamic quantization configuration.

Example:

```python
from sentence_transformers import (
    SentenceTransformer,
    export_dynamic_quantized_onnx_model,
)

model = SentenceTransformer(
    "sonarbird-onnx",
    backend="onnx",
)

export_dynamic_quantized_onnx_model(
    model=model,
    quantization_config="arm64",
    model_name_or_path="sonarbird-onnx",
    push_to_hub=False,
)
```

Inspect the exported output filename and model metadata rather than assuming the name.

Retain separate builds:

- ONNX FP32 reference.
- ONNX INT8 ARM64 candidate.

Compare:

- Embedding similarity.
- Route agreement.
- Classification accuracy.
- Latency.
- Memory use.
- CPU usage.
- Thermal effects.
- Energy per routed request.

Do not deploy INT8 solely because it has a smaller file.

If INT8 causes unacceptable routing errors or performs worse on the actual S10+, keep FP32 or evaluate another supported configuration.

Do not use x86 AVX-specific quantization settings for the Exynos9820.

# 12. Integrate SonarBird into the Existing Squad

Preserve the existing routing architecture and API conventions.

Find the current SonarBird service and replace its missing-model or placeholder classification logic with genuine inference.

Use a narrow typed interface.

Suggested logical request:

```json
{
  "text": "Can you fix this Python function?",
  "mode": "AUTO",
  "source": "penguru"
}
```

Suggested logical response:

```json
{
  "route": "CODE",
  "decision": "MODEL",
  "abstained": false,
  "scores": {
    "CHAT": 0.08,
    "CODE": 0.90,
    "SYSTEM": 0.02
  },
  "model": "all-MiniLM-L6-v2",
  "classifier_version": "sonarbird-routing-v1",
  "latency_ms": 0
}
```

The values above are illustrative schema examples, **not measured model outputs**.

If confidence is not calibrated, label scores as raw or uncalibrated.

Add appropriate request validation and response-size limits.

Use the existing local IPC, D-Bus or service infrastructure rather than adding a publicly reachable HTTP server.

Route to the existing working CodeBird process without changing its model-loading implementation.

Implement timeouts, worker failure handling, cancellation, version reporting and structured errors.

No private user text should be included in normal service logs by default.

# 13. Handle Multiple Intents

Test mixed requests such as:

"Explain this Python function, then change my brightness."

This contains conversational/code and system-action elements.

Do not silently execute a system operation merely because the classifier assigns SYSTEM.

Initially, treat mixed intents as ambiguous and require an explicit user decision if necessary.

If the existing Squad architecture supports multi-step task decomposition, integrate only through its trusted orchestrator and permission broker.

Do not add autonomous chains of privileged actions to the routing classifier.

# 14. Make SonarBird Battery-Efficient

The S10+ is a constrained ARM64 platform compared with a desktop.

Optimize for short, occasional inference requests.

Recommended starting strategy:

- CPUExecutionProvider.
- Benchmark one, two and four inference threads.
- Keep maximum input length bounded.
- Batch only where it improves actual responsiveness.
- Cache the tiny classification head.
- Avoid unnecessary background inference.
- Avoid continuous microphone or wake-word processing.
- Never load a second large generative model merely for routing.
- Respect Nuxel battery-saver and thermal policies.
- Let the existing resource manager control lifecycle and memory budgets.

Determine experimentally whether keeping the small encoder resident or unloading it after inactivity gives the best battery/latency trade-off.

Do not assume always-resident means high drain; idle wakeups and memory pressure matter more than a static model file occupying memory.

Conversely, do not assume repeatedly cold-loading the encoder is always more efficient.

Measure both strategies.

Ensure model initialization does not block Nuxel's main UI thread.

# 15. Performance Benchmarks

Test on the actual Galaxy S10+.

Capture:

- Cold model-load time.
- Warm single-request latency.
- p50/p95 routing latency.
- Peak memory.
- Idle CPU usage.
- Model file size.
- CPU thread count.
- Request throughput.
- Battery current and voltage where available.
- Energy per classification.
- Temperature and throttling.
- Idle/wake behavior.
- Latency while ChatBird is running.
- Latency while CodeBird is running.
- Memory availability after worker unload.

Compare FP32 and INT8 using the same labeled inputs and device conditions.

Aspirational quality gates:

- High held-out macro-F1.
- Strong CODE precision and recall.
- Very low SYSTEM false-positive rate.
- Stable, predictable abstention behavior.
- No unauthorized system actions.
- No measurable excessive background wakeups.

Set numerical targets in the project test policy and justify them with the actual risk and usability requirements.

Do not invent performance or energy figures.

If a model is too slow, profile tokenizer, pooling, ONNX Runtime, threading and cold-loading separately before replacing MiniLM.

# 16. Test Matrix

Create automated tests covering:

### Semantic correctness

- CHAT requests.
- CODE requests.
- SYSTEM requests.
- Ambiguous requests.
- Unknown inputs.
- Long inputs.
- Empty input.
- Multiline input.
- Code blocks.
- Quoted commands.
- Technical terminology.
- Typographical errors.
- Unsupported languages.

### Routing correctness

- Manual mode overrides.
- Classifier abstention.
- System requests requiring permission.
- Model unavailable.
- Missing tokenizer.
- Corrupt model.
- Wrong classifier dimensions.
- Invalid or outdated classifier manifest.
- Cancelled request.
- Inference timeout.
- Competing model workers.

### Security

- SYSTEM routing cannot bypass Supervisor.
- Untrusted text cannot grant permissions.
- Model output cannot directly execute code.
- No arbitrary shell exposure.
- No unsigned model substitution.
- No private conversation logging by default.
- No network access required for local classification.

### Numerical parity

- PyTorch/Sentence Transformers reference.
- ONNX FP32.
- ONNX INT8.
- Correct tokenization.
- Correct attention masking.
- Correct normalization.
- Matching route behavior.

### Physical device acceptance

- Genuine SonarBird inference on S10+.
- Correct CodeBird handoff.
- Correct ChatBird handoff.
- Correct Supervisor permission flow.
- No crash or system instability.
- Stable background battery behavior.
- Working cancellation and restart.

Report host simulations and physical device verification separately.

# 17. Training Quality Improvements

After the baseline is functioning, inspect the confusion matrix.

For each repeated failure category:

1. Identify the semantic confusion.
2. Add diverse, manually reviewed examples.
3. Add counterexamples for the neighboring route.
4. Retrain the classifier head.
5. Recalibrate uncertainty handling.
6. Reevaluate the untouched test set.
7. Investigate any regression.

Do not improve apparent accuracy by adding test examples directly to training.

If the frozen encoder reaches a genuine performance ceiling, evaluate task-specific fine-tuning using a separate experiment.

Compare the fine-tuned variant against the frozen baseline on identical held-out data.

Only promote the fine-tuned variant if its gains justify its additional model-management and maintenance costs.

# 18. Model Store and Deployment

Integrate SonarBird with Nuxel's existing model management system.

Create the required manifest using the repository's actual schema.

Include:

- Model name and source repository.
- Exact upstream revision.
- Model license.
- Original file hashes.
- ONNX export tool versions.
- INT8 quantization tool versions and configuration.
- Tokenizer identity.
- Pooling and normalization strategy.
- Classification labels.
- Classifier head version.
- Training dataset version/hash.
- Calibration parameters.
- Evaluation summary.
- Target architecture.
- Supported inference provider.
- Artifact integrity hashes.

Honor existing signature verification requirements.

Do not commit downloaded model weights to the normal source repository unless the project explicitly uses an approved model artifact mechanism.

Prefer an atomic deployment that preserves the previously working routing implementation.

Maintain a rollback path if the model fails to load or produces unacceptable classifications.

Do not alter the working CodeBird model.

# 19. Required Deliverables

Create or update the appropriate repository files, adapting names to the actual architecture.

Expected deliverables include:

1. MiniLM model acquisition and pinning script.
2. Reproducible host training pipeline.
3. Reviewed routing dataset.
4. Frozen-encoder classification head.
5. Validation and calibration tool.
6. ONNX FP32 export.
7. ARM64 INT8 export candidate.
8. Pooling/normalization parity tests.
9. Actual SonarBird runtime integration.
10. Squad routing integration.
11. Security and permission regression tests.
12. Performance and battery benchmark scripts.
13. Model Store manifest and packaging.
14. Live S10+ acceptance evidence.
15. Updated PenGuru documentation.

Create a final report:

`reports/SONARBIRD-MINILM-IMPLEMENTATION.md`

The report must include:

- Starting and final Git commits.
- Model revision and hashes.
- Classifier training details.
- Routing confusion matrix.
- Per-class precision/recall/F1.
- Confidence/abstention calibration.
- FP32 versus INT8 results.
- On-device latency.
- Memory measurements.
- Battery/thermal measurements.
- Integration tests.
- Physical S10+ verification.
- Known limitations.
- Reproducible installation instructions.

# 20. Final Acceptance Criteria

SonarBird is ready for the PenGuru beta only when:

- The actual MiniLM model loads locally.
- Genuine inference runs on the S10+.
- The classifier produces validated routing decisions.
- CHAT correctly reaches ChatBird.
- CODE correctly reaches the already-working CodeBird.
- SYSTEM reaches only the authorized Supervisor path.
- Ambiguous requests have a safe fallback.
- Model integrity checks are enforced.
- ONNX pooling and classification parity are verified.
- Performance is acceptable on the target device.
- Background resource consumption is bounded.
- The existing permission system remains intact.
- The system can be disabled or rolled back.

No model output can authorize a privileged operation.

# 21. Execution Instructions

Begin immediately with the actual repository audit.

Then work through the phases in dependency order.

Do not stop at downloading MiniLM.

Do not stop when ONNX export succeeds.

Do not stop when the classifier produces a label.

Continue until the full PenGuru routing path is physically verified on Nuxel, or a specific external blocker prevents further safe work.

For each milestone:

1. Investigate the relevant implementation.
2. Reuse existing project code.
3. Implement the necessary correction.
4. Run meaningful tests.
5. Record evidence.
6. Commit a focused change.
7. Continue to the next milestone.

Preserve all unrelated work.

Do not fabricate benchmarks or routing accuracy.

Avoid unnecessary model architecture changes.

**Your immediate priority is a frozen MiniLM encoder plus a trained and validated 384-dimensional classification head, followed by a genuinely functioning ONNX-powered SonarBird router on the S10+.**

## Final objective

Build a SonarBird that is:

**Tiny enough for mobile. Fast enough to be unobtrusive. Accurate enough to route reliably. Safe enough to never grant permissions. Fully offline. And deeply integrated into PenGuru Squad.**

The final success condition is not that MiniLM produces embeddings.

It is that **PenGuru automatically sends real requests to the correct subsystem, with measured accuracy, reasonable battery consumption and enforced permissions, on the actual Nuxel S10+.**
