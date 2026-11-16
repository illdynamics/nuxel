PENGURU SQUAD

DUAL-RUNTIME IMPLEMENTATION GUIDE

ChatBird • CodeBird • SonarBird

A native, local-first Nuxel AI subsystem with selectable llama.cpp and
ONNX Runtime GenAI backends

Version 1.1 \| 9 November 2026

"PenGuru may suggest anything, may prepare what it can verify, and may
change only what its owner authorizes."

Architecture brainstorm + repository-grounded build specification

# Document purpose and status

This is a revised implementation guide for PenGuru in Nuxel. It
incorporates the supplied NuXAI architecture brainstorm, the earlier
PenGuru Squad specification, the uploaded Nuxel source archive audit,
and current upstream runtime/model documentation checked on 9 November
2026.

The central revision is to separate three independent choices that must
not be conflated: (1) which assistant mode the owner chooses, (2) which
generative inference runtime is used for a given model, and (3) which
hardware execution provider is available on the current device. This
keeps the user experience stable while allowing the inference engine and
hardware path to evolve.

| Important compatibility rule The supplied ChatBird and CodeBird
  downloads are GGUF files. They load directly in llama.cpp. They do not
  become ONNX models because ONNX Runtime is installed. To use ONNX
  Runtime GenAI for those workers, build and validate separate ONNX
  packages from the corresponding original Transformers-format
  checkpoints. The GGUF and ONNX packages are distinct artifacts with
  separate manifests and hashes. \|

| --- \|

| Repository scope The ZIP archive was available and inspected. The
  earlier audit count was 20,105 ZIP entries / 18,068 files. The prior
  guide records selected regression suites and source-level findings.
  This document carries those findings forward; it does not claim
  PenGuru already exists in the repository. \|

| --- \|

## How to read this guide

"Observed" means found in the uploaded repository or a cited current
upstream source.

"Proposed" means a design decision or new component to implement.

"Gate" means do not ship the feature until its measurable exit criteria
pass.

Model and runtime facts are not performance promises. Only benchmarks on
exact Nuxel images and phone SKUs can establish real-world speed, memory
use, temperature and battery cost.

# Executive architecture decisions

| Decision axis \| Owner-selectable values \| Meaning \|

| --- \| --- \| --- \|

| Assistant mode \| Single ChatBird / Single CodeBird / PenGuru Squad \|
  Controls whether requests are sent directly to one worker or routed by
  SonarBird. \|

| Generative LLM backend \| Auto / llama.cpp / ONNX Runtime GenAI \|
  Controls the engine used to run ChatBird or CodeBird. It is
  constrained by which package variant is installed and verified. \|

| Hardware execution provider \| CPU / validated GPU provider /
  validated NPU provider \| Controls where kernels execute. This is
  separate from the model format and LLM engine. \|

| SonarBird classifier engine \| ONNX Runtime (standard inference API) +
  deterministic rules \| Runs the small embedding/classifier package in
  Squad mode. It is not an LLM and does not require ORT GenAI. \|

| Network policy \| Offline / user-started downloads \| No prompt
  telemetry or remote model fallback in v1. LAN inference remains a
  future adapter, disabled by default. \|

| Recommended default Ship llama.cpp first for the provided GGUF files;
  ship the ONNX Runtime GenAI adapter as a first-class, toggleable
  backend once each model has a verified ONNX package. Keep ONNX Runtime
  standard available for SonarBird even when the generative backend
  preference is set to llama.cpp. \|

| --- \|

## Release gates

| Gate \| Required proof before release \|

| --- \| --- \|

| G0 --- privilege safety \| Harden the root-owned HTTP bridge
  development path and fix once/session grant cache semantics. No
  privileged PenGuru operation before this. \|

| G1 --- llama.cpp \| Pinned ARM64 build loads the exact ChatBird and
  CodeBird GGUFs, correct chat templates, cancellation and memory
  release. \|

| G2 --- ONNX Runtime \| Pinned ONNX Runtime + ONNX Runtime GenAI Linux
  ARM64 build loads each published ONNX worker bundle. SonarBird ONNX
  classifier also passes its own accuracy tests. \|

| G3 --- device profile \| Measurements on exact phone SKUs: RSS/PSS,
  time-to-first-token, prompt/decode speed, cold load, heat, battery and
  memory pressure. \|

| G4 --- artifact provenance \| Signed immutable manifests, revisions,
  hashes, file lists, tokenizer/config hashes, license notices and
  export provenance. \|

| G5 --- product/security \| All three modes, runtime selection, offline
  operation, hostile-input tests, approvals, rollback and user-visible
  routing pass. \|

# Contents

1.  Product scope, vocabulary and invariants

2.  Repository audit and required fixes

3.  Product modes and runtime-selection experience

4.  Reference architecture and request lifecycle

5.  Runtime abstraction: llama.cpp and ONNX Runtime

6.  Model packages, compatibility and model download cards

7.  SonarBird routing and training pipeline

8.  Model Manager, scheduler and persistent queue

9.  NuXAI service architecture and Nuxel integration

10. Supervisor, security and capability model

11. Download, update and integrity pipeline

12. Devices, memory, acceleration and power

13. Voice, privacy and network policy

14. API contracts and configuration examples

15. Testing, acceptance criteria and release evidence

16. Phased implementation roadmap

17. Risks, design choices and launch checklist

Appendix A. Proposed repository layout

Appendix B. External technical references

# 1. Product scope, vocabulary and invariants

## 1.1 What PenGuru is

PenGuru is the user-facing local assistant and OS-engineering workflow
in Nuxel. It uses three logical model roles: ChatBird for conversation
and explanations, CodeBird for code and extension work, and SonarBird
for lightweight request routing. The user chooses one of three modes;
the model runtime can be selected independently wherever a compatible
package exists.

NuXAI is the proposed underlying Nuxel AI infrastructure: the control
plane, runtime adapters, model store, scheduler and local inference API.
PenGuru is the native app/product that uses that infrastructure. Other
Nuxel apps may later use the NuXAI inference API without embedding a
model runtime themselves.

## 1.2 Roles and boundaries

| Component \| Owns \| Must never do \|

| --- \| --- \| --- \|

| ChatBird \| General conversation, explanation, brainstorming and
  summarization. \| Execute shell commands, choose permissions, change
  the OS or approve actions. \|

| CodeBird \| Code explanation, debug suggestions, patch proposals,
  scripts, tests and extension scaffolds. \| Install or execute
  generated code outside the Supervisor-controlled workspace. \|

| SonarBird \| In Squad mode: classify CHAT / CODE / SYSTEM / ASK and
  explain the decision. \| Listen to ambient audio or inspect screen
  continuously; execute tools; grant permissions; approve changes. \|

| NuXAI Runtime Manager \| Select compatible runtime and provider,
  start/stop worker, expose inference stream. \| Trust model outputs as
  commands or bypass the service policy. \|

| PenGuru Supervisor \| Validate typed proposals, permission state,
  workspaces, tests, approval hashes and rollback. \| Accept
  model-supplied approval flags or arbitrary shell strings as actions.
  \|

| Nuxel permission authority \| Authenticate app identity and enforce
  canonical capabilities / consent. \| Trust caller identity supplied
  inside untrusted JSON or model output. \|

## 1.3 v1 scope

Optional feature, disabled by default. When disabled, NuXAI stops its
PenGuru-specific daemons, classifier and worker processes and releases
their memory.

Text-first local operation, with a native chat/control UI, conversation
history policy, request queue, cancellation and status feedback.

Three operating modes: Single ChatBird, Single CodeBird and Squad
(SonarBird dispatcher).

Toggleable generative runtime: llama.cpp for GGUF and ONNX Runtime GenAI
for verified ONNX packages. Standard ONNX Runtime is used for SonarBird
embeddings/classifier.

Exactly three logical model cards/download controls: ChatBird, CodeBird
and SonarBird. Each card can expose verified package variants, without
pretending file formats are interchangeable.

Permissioned read-only diagnostics and a staged extension/code workflow;
safe write operations only after broker hardening.

CPU inference baseline. GPU or NPU execution only when the exact device,
driver, kernel and runtime provider are verified.

## 1.4 Explicitly deferred

Always-on microphone and wake-word detection in the first release. Add a
separate opt-in foreground voice feature after privacy, background and
power testing.

Cloud fallback or automatic remote inference. A LAN worker may be added
later as a distinct, opt-in provider.

Autonomous kernel, boot-chain, partition, driver or root/sudoers
changes.

Online learning or training model weights on the phone. Model
"self-improvement" means supervised creation of Nuxel extensions, not
unreviewed changes to LLM weights.

Mandatory GPU/NPU acceleration. CPU-only inference must remain a
reliable baseline.

# 2. Repository audit and required fixes

Audit basis: uploaded `nuxel-main (4).zip`, inspected in the session.
The archive contains 20,105 ZIP entries and 18,068 files. The repository
contains useful native infrastructure but no PenGuru implementation, no
ChatBird/CodeBird/SonarBird integration, no packaged GGUF models and no
llama.cpp runtime integration were found in the audited source.

## 2.1 Existing foundations to reuse

| Repository area \| Observed role \| Integration decision \|

| --- \| --- \| --- \|

| `services/nuxel-bridge/` \| PWA-to-native bridge, D-Bus methods,
  capability checks, phone/system providers and a separate HTTP bridge.
  \| Reuse typed non-privileged methods and add only narrowly defined
  PenGuru adapters after identity and grant fixes. \|

| `services/nuxel-portal/` \| Consent portal with once/session/always
  grant semantics, timeouts and fail-closed policy. \| Reuse the consent
  experience and lifecycle; do not add a parallel permission prompt
  system. \|

| `shell/nuxel-shell/nuxel-permissions/` \| `nuxel-permd.py`, canonical
  `capabilities.json`, grant store, policy review, kernel facts and
  enforcement planning. \| Treat its capability registry as canonical.
  Add PenGuru scopes there and validate mappings in CI. \|

| `pwa/nuxel-common/bridge.js` \| Shared PWA bridge client. \| Use
  shared transport; do not fork a PenGuru-only implementation. \|

| `pwa/nuxel-common/bridge-version.json` \| Pinned bridge protocol
  version 1. \| Keep additive API changes compatible; bump only for
  breaking schema/transport changes. \|

| `pwa/nuxel-common/app-registry.json` \| Canonical PWA app registry. \|
  Register PenGuru as its own app through the existing build and asset
  pipeline. \|

| `pwa/nuxel-apps/penguinterface/` \| Read-only compatibility/profile UI
  with `system:inspect` capability. \| Use as a UI and diagnostics
  reference, not as a privileged PenGuru runtime. \|

| `services/nuxel-session/`, `services/nuxel-notifications/` \| Session
  identity and notification/status infrastructure. \| Use for approval
  prompts and status after authenticated caller/session binding is
  correct. \|

| Makefile, `tools/dedupe-assets.sh`, `ci/validate-build.sh` \| Build,
  PWA asset population and validation. \| Add PenGuru service, app,
  schema and manifest validation to the canonical pipeline. \|

## 2.2 Existing test baseline

| Command / suite \| Observed result \| Interpretation \|

| --- \| --- \| --- \|

| `python3 services/nuxel-portal/test-portal-policy.py` \| All portal
  policy checks passed. \| Portal-side policy semantics pass current
  repository tests. \|

| `python3 services/nuxel-bridge/test-grant-store.py` \| ALL PASS. \|
  File parsing tests pass; does not test bridge one-shot cache
  semantics. \|

| `python3 shell/nuxel-shell/nuxel-permissions/tests/test-policy-defaults.py`
  \| 13/13 passed. \| Canonical registry/defaults and fail-closed
  defaults pass. \|

| `python3 shell/nuxel-shell/nuxel-permissions/tests/test-permissions.py`
  \| 24 tests passed. \| Permission store, enforcement review,
  unsupported capabilities and audit tests pass. \|

| `node pwa/nuxel-apps/rootcontrol/tests/test-privilege-model.js` \| 25
  passed, 0 failed. \| The RootControl model reports documented Linux
  4.14 kernel limitations. \|

| `node pwa/nuxel-common/verify-wiring.js` \| All six PWA surfaces OK.
  \| Current surfaces use the shared bridge client/version wiring. \|

Test caveat: these are repo tests from the prior audit. They do not
prove production boot, security of every alternate bridge path, real
kernel isolation or PenGuru functionality. New PenGuru tests and
on-device tests are mandatory.

## 2.3 P0 finding --- root-owned HTTP bridge development mode

Observed source:
`services/nuxel-bridge/systemd/nuxel-http-bridge.service` runs as root,
binds loopback at 127.0.0.1:8080 and sets `NUXEL_HTTP_MODE=dev`. In
`services/nuxel-bridge/src/api.py`, `_verify_auth()` accepts loopback
requests without a token in development mode. The API also has an
unauthenticated token bootstrap route accepting an app identifier; later
request handling reads the app identifier from request JSON, while token
validation does not adequately bind the body identity to the token
identity. The service-control helper gates based on an app-id allowlist.
This must not become PenGuru's privilege boundary.

Build production images with development loopback bypass disabled; fail
the build if the production unit or environment can enable it.

Bind every session token to a trusted launcher-authenticated app
identity. Enforce token app identity equals request app identity for
every method.

Derive caller identity from a trusted launcher or authenticated D-Bus
peer credentials, not a JSON body, Origin or Referer header.

Create a typed PenGuru broker surface over the canonical permission
service; do not route privileged actions through generic HTTP `/rpc` or
owner-only service-control helpers.

Add tests for forged app_id, token replay across apps, app identity
mutation, missing launcher secret, untrusted loopback and unauthorized
service control.

## 2.4 P1 finding --- once/session grant cache semantics

Observed source: `services/nuxel-bridge/src/bridge.py`
`_check_capability()` can return true from an in-memory cache before
consulting the portal. A cached once/session grant may therefore be
reusable beyond the portal's intended one-shot/session lifecycle until
cache eviction, revocation or daemon restart.

Never cache a `once` grant as reusable. Consume the grant at the
permission authority, bound to one immutable action/request ID.

Bind `session` grants to a real session identifier with explicit expiry
and revocation events.

Persist `always` only where policy expressly permits it; use monotonic
time for in-process expiry.

Add a bridge-level regression proving the first once action succeeds and
the second action fails within the same daemon lifetime.

## 2.5 P1 finding --- capability registry drift

The repository contains a canonical `nuxel-permd` capability registry
alongside bridge-side capability declarations and another capability
module. PenGuru must not create a fourth independent definition.
Generate or validate PenGuru and bridge adapter schemas from the
canonical registry, and deny unknown capability names.

## 2.6 P1 finding --- sandbox claims must reflect the kernel

The RootControl code/tests explicitly model Linux 4.14.253 constraints.
Landlock is not present on that kernel; AppArmor/SELinux are not
asserted as active; the effective boundary is DAC, Linux capabilities,
seccomp and selected systemd unit sandbox settings. `DeviceAllow=` may
not be effective where the BPF device controller is unavailable. The
Supervisor must probe real kernel features and report which isolation
primitives are effective. If a sufficiently isolated code runner is
unavailable, disable code execution and permit only patch review/export.

| Integration rule PenGuru may be developed in chat-only mode while
  these defects are fixed. It must not receive privileged capabilities
  or install generated code until the P0/P1 issues are closed and
  independently regression-tested. \|

| --- \|

# 3. Product modes and runtime-selection experience

## 3.1 The mode selector

| Mode \| Request path \| Worker behaviour \| SonarBird \|

| --- \| --- \| --- \| --- \|

| Single ChatBird \| Every prompt -\> ChatBird. \| ChatBird loads on
  demand and handles the request. \| Bypassed entirely for routing. \|

| Single CodeBird \| Every prompt -\> CodeBird. \| CodeBird loads on
  demand and handles the request. \| Bypassed entirely for routing. \|

| PenGuru Squad \| Request -\> SonarBird -\> CHAT / CODE / SYSTEM / ASK.
  \| Load only ChatBird or CodeBird for CHAT/CODE. SYSTEM uses typed
  APIs. ASK waits for clarification. \| Runs for each Squad request
  only. \|

## 3.2 The independent runtime selector

The runtime selector applies to generative workers, not to mode
selection. Recommended settings UI:

| Setting \| Values \| Behaviour \|

| --- \| --- \| --- \|

| Preferred LLM Runtime \| Auto / llama.cpp / ONNX Runtime GenAI \| Auto
  chooses a compatible installed package according to the user's
  preferred order. Explicit selection requires a compatible verified
  artifact. \|

| Enable llama.cpp \| On / Off \| Enables the GGUF adapter and all
  pinned llama.cpp model profiles. \|

| Enable ONNX Runtime GenAI \| On / Off \| Enables the ONNX LLM adapter
  only where ONNX GenAI package and model assets are installed. \|

| SonarBird ONNX classifier \| Managed by Squad \| Uses standard ONNX
  Runtime session inference for MiniLM + classifier package. This is not
  the generative backend toggle. \|

| Execution provider \| Auto / CPU / available providers \| Only shows
  provider options compiled into the installed runtime and validated on
  this device. \|

| Per-model override \| Inherit / llama.cpp / ORT GenAI \| Allows
  ChatBird and CodeBird to use different backends when both artifacts
  are installed. \|

| Important distinction Disabling ONNX Runtime GenAI for
  ChatBird/CodeBird does not uninstall the standard ONNX Runtime
  component used by SonarBird. In Single ChatBird or Single CodeBird
  mode, SonarBird is not loaded, so its classifier dependency can be
  idle. In Squad mode, the ONNX classifier must be available or the
  router must fall back to deterministic rules and ASK. \|

| --- \|

## 3.3 Compatibility and fallback rules

An explicit runtime choice is a constraint, not a suggestion. If the
required package is missing or incompatible, show "not available" and
explain why.

Never silently send a GGUF file to ONNX Runtime GenAI, or an ONNX
package to llama.cpp, unless a separately verified adapter for that
format exists.

Auto mode may choose a compatible backend based on signed package
metadata. The UI must display the actual backend and provider used for
each request.

No automatic cross-runtime fallback after generation has started; that
could change tokenization, sampling, prompt templates and output. A
failed load can offer a user-approved switch before retry.

Runtime selection never changes the permission model, Supervisor checks,
audit trail or tool allowlist.

## 3.4 Example UI state

Mode: \[ PenGuru Squad v \] Preferred LLM runtime: \[ Auto v \] \[x\]
llama.cpp \[x\] ONNX Runtime GenAI ChatBird packages: GGUF installed \|
ONNX package available / not installed CodeBird packages: GGUF installed
\| ONNX package available / not installed SonarBird: ONNX classifier
installed \| Rules fallback ready Execution provider: CPU (validated) \|
Vulkan (not validated) \| NPU (unavailable) Active request: CodeBird •
llama.cpp • CPU • 4 threads • 4096 context

# 4. Reference architecture and request lifecycle

## 4.1 System layers

Nuxel shell / PenGuru PWA / other trusted Nuxel clients \| authenticated
D-Bus / shared PWA bridge v NuXAI Control Plane (unprivileged) - mode
controller + request queue (SQLite) - routing facade + SonarBird
rules/classifier - model registry + download manager - runtime
selector + resource scheduler - conversation service + audit metadata \|
+--------+------------------------------+ \| \| v v SonarBird classifier
Worker Manager rules + ORT encoder one heavy worker at a time \| \|
+--\> CHAT / CODE / SYSTEM / ASK +--\> llama.cpp adapter (GGUF) +--\>
ORT GenAI adapter (ONNX bundle) \| v Unified Inference API \| v PenGuru
Supervisor - typed proposal schemas - isolated workspace/tests -
approval hash + audit \| v nuxel-permd / portal / bridge adapter \| v
typed Nuxel APIs / controlled install

NuXAI is the common service layer. The runtime adapters are plug-ins
behind one stable API. The UI must not know whether a given request ran
on llama.cpp or ONNX Runtime except to display the chosen runtime and
its performance/status details.

## 4.2 Request lifecycle in Squad mode

Client sends text, conversation ID, selected mode, optional
project/workspace reference and request metadata to `org.nuxel.PenGuru`.

The service authenticates the caller, checks session ownership, limits
payload size and request queue depth, and stores a request record.

SonarBird applies deterministic Tier 0 rules. If those rules do not make
a high-precision decision, it runs the embedding classifier using
standard ONNX Runtime.

SonarBird returns only a constrained route label, calibrated confidence,
reason code and classifier version. It does not output permissions or
arbitrary tool parameters.

CHAT loads ChatBird; CODE loads CodeBird; SYSTEM invokes an allowlisted
typed capability through Supervisor; ASK requests clarification without
loading a heavy worker.

Runtime Manager chooses an installed package variant and the selected
backend, verifies memory/thermal budget and starts the worker.

The worker receives a bounded prompt assembled from user content and
explicitly selected trusted context. External documents, repository
files and logs remain untrusted data.

Generated content returns as text or a typed proposal. Supervisor
validates schemas, stages code, runs only allowed tests in isolation,
constructs a preview and hashes the exact action.

The portal asks the owner to approve the exact proposal. The broker
checks identity, scope, current grant and capability again immediately
before execution.

The system records result, audit reference and rollback handle where
available. Worker is unloaded by policy after the request/idle period.

## 4.3 Request lifecycle in single mode

Single ChatBird and Single CodeBird bypass SonarBird completely for that
request path. The selected model is the direct target. This does not
disable the Supervisor, capability broker, schema validation, approvals
or audit. A tool-like string in a model response is inert text unless a
separate typed Nuxel UI action initiates it.

## 4.4 SYSTEM is not another LLM

SYSTEM requests should be resolved by deterministic intent and an
explicit user-facing command/API contract. Examples: battery state,
Wi-Fi state, volume, Bluetooth status or service diagnostics. For
writes, the user chooses a visible action and Nuxel permission policy
decides whether a confirmation is needed. SonarBird may suggest SYSTEM,
but a classifier confidence score is never sufficient authorization.

# 5. Runtime abstraction: llama.cpp and ONNX Runtime

## 5.1 Why a runtime abstraction is worth building

Do not make the PenGuru application or operating system depend directly
on llama.cpp command-line flags. Define a stable `InferenceRuntime`
interface and provide versioned adapters. GGUF is the direct model
format for llama.cpp; ONNX Runtime GenAI uses ONNX model graphs and a
generation configuration package. The abstraction allows both engines to
be selectable without forcing the same weights or packaging across them.

## 5.2 Runtime interface

interface InferenceRuntime { ProbeResult probe(DeviceProfile,
RuntimeProfile); LoadResult load(ModelPackage, RuntimeProfile);
Stream`<InferenceEvent>`{=html} generate(ValidatedPrompt,
GenerationOptions); CancelResult cancel(RequestId); HealthResult
health(); UnloadResult unload(Reason); RuntimeInfo info(); }

RuntimeProfile { engine: LLAMA_CPP \| ORT_GENAI; package_format: GGUF \|
ONNX_GENAI; provider: CPU \| VULKAN \| XNNPACK \| ACL \| ARM_NN \|
OTHER_VALIDATED; threads: integer; context_limit: integer; batch_limit:
integer; memory_budget_bytes: integer; }

This is a conceptual contract, not code that can be copied without
adapting to the Nuxel language, build system and daemon interface.
Runtime adapters should expose common events: loading, loaded, token,
progress, cancelled, out-of-memory, error and unloaded.

## 5.3 llama.cpp adapter --- GGUF path

llama.cpp is the primary v1 engine for the two supplied GGUF downloads.
It is a native C/C++ project built on ggml, supports quantized weights
and CPU inference, and has multiple optional backends including Vulkan
and other hardware paths depending on build support. Its server offers
OpenAI-compatible APIs and structured-output features, but Nuxel should
not expose a general-purpose model server or its optional filesystem
tools to arbitrary local clients. \[R1\]\[R2\]

Build a reproducible ARM64 package from a pinned commit/tag. Record
source commit, compiler, CMake flags, linked backend libraries, SBOM and
binary hashes.

CPU is the baseline: compile and benchmark ARM NEON-capable kernels; use
any additional ARM optimizations only if detected and tested for the
phone CPU.

Prefer an in-process C/C++ adapter or a tightly sandboxed worker process
over launching a general REST server. If a child server is used for
development, bind only to a private interface, disable tools, use a
strong ephemeral credential and prevent LAN exposure.

Use the exact GGUF metadata/chat template, tokenizer metadata, BOS/EOS,
stop sequences and generation defaults. Do not hard-code Llama templates
for Qwen or vice versa.

Expose controlled limits for threads, context, batch, KV-cache type, CPU
affinity and GPU layers. Start conservative and collect memory profiles
per model/device.

Use model-specific self-tests at load time: metadata parse, architecture
identification, template presence, tokenizer sanity, short prompt
generation and clean cancellation.

On unload, stop accepting new requests, cancel/finish bounded
generation, release contexts and confirm worker RSS falls below the
expected baseline.

### Production integration pattern

Recommended: `nuxel-penguru` owns the scheduler and starts an
unprivileged `nuxel-ai-worker` with an IPC endpoint protected by Unix
peer credentials and filesystem permissions. The worker embeds or links
a pinned llama.cpp build. No TCP listener is required for the
application path. The llama.cpp HTTP server can remain a developer
benchmark tool only.

## 5.4 ONNX Runtime adapter --- ONNX generation path

Separate two technologies that are often casually called "ONNX Runtime".
Standard ONNX Runtime executes ONNX graphs; it is sufficient for
SonarBird embedding/classifier inference. Generative LLM inference needs
the generation loop, tokenization/chat-template handling, logits
processing, sampling and KV-cache management. Microsoft provides ONNX
Runtime GenAI for this layer. The official Generate API documentation
currently labels it Preview and says the API may change; keep it behind
a versioned adapter. \[R3\]

Package the exact ONNX Runtime and ONNX Runtime GenAI versions as one
tested compatibility set. Do not mix arbitrary provider binaries from
different core versions.

Build model bundles from original Transformers-format checkpoints, not
from the distributed GGUF files. Use a pinned ONNX Runtime GenAI
model-builder version and record every builder option.

Bundle `genai_config.json`, ONNX graph(s), external tensor weight
shards, tokenizer assets, tokenizer configuration, generation
configuration and all required model metadata.

Create model package variants per provider/precision only when they are
genuinely different artifacts. CPU and accelerator-specific graphs may
require separate manifests.

Test tokenizer/chat template parity against the source checkpoint:
system message, multi-turn history, stop tokens, EOS handling, special
tokens and structured output.

Keep a CPU execution provider fallback. Add XNNPACK or ARM ACL/Arm NN
only if the runtime binary is compiled with them and the target profile
passes functional and performance tests.

On errors such as unsupported operator, provider fallback, graph
mismatch or KV-cache mismatch, fail closed and report a specific
compatibility status; do not silently load the GGUF through another
backend.

Current feasibility signal: ONNX Runtime GenAI model-builder
documentation lists Llama and Qwen support. Its current upstream release
list includes v0.17.0 (28 September 2026) and Linux ARM64 assets; recent
model-builder documentation discusses Qwen3.5/3.8 export details. This
makes ONNX exports technically plausible for these two model families,
but does not prove the exact fine-tunes, quantization choices or Nuxel
ARM64 CPU path are already validated. \[R4\]\[R5\]

## 5.5 Runtime compatibility matrix

| Model \| llama.cpp \| ONNX Runtime GenAI \| Decision \|

| --- \| --- \| --- \| --- \|

| ChatBird \| Direct GGUF path; Q4_K_M artifact is published. \|
  Candidate from the original Transformers checkpoint: architecture is
  Llama-family and ONNX GenAI builder supports Llama. Must export/test
  the exact fine-tune, tokenizer and template. \| Ship GGUF first. Add
  ONNX bundle only after exact checkpoint export and parity acceptance.
  \|

| CodeBird \| Direct GGUF path; requires a recent Qwen3.5/Gated
  DeltaNet-capable llama.cpp build. \| Candidate from
  `empero-ai/Qwen3.8-4B-Distill` Transformers checkpoint. Current ORT
  GenAI tooling includes Qwen3.5/3.8 support. Must validate
  checkpoint/config and ARM64 provider support. \| Ship GGUF first. The
  source Transformers checkpoint is the correct input for ONNX export,
  not the GGUF file. \|

| SonarBird \| Not needed for the proposed MiniLM ONNX classifier. A
  future GGUF embedding model would be a different artifact. \| Standard
  ONNX Runtime session for sentence embedding + pooling + classifier
  head. ORT GenAI is not needed. \| Keep SonarBird as a small
  independent ONNX inference component in Squad mode. \|

## 5.6 Runtime preference algorithm

resolve_backend(model, user_preference): candidates =
verified_installed_packages(model) if user_preference == LLAMA_CPP:
require candidate with format GGUF and pinned llama.cpp profile else
return BACKEND_UNAVAILABLE if user_preference == ORT_GENAI: require
candidate with format ONNX_GENAI and compatible ORT profile else return
BACKEND_UNAVAILABLE if user_preference == AUTO: choose the
highest-priority verified candidate allowed by policy prefer the saved
per-model preference, else device default probe provider + memory +
thermal budget return explicit chosen engine, provider, package revision

The UI must show the resolved engine, package revision and provider
before generation begins. "Auto" must never mean "try random runtimes
until one works".

## 5.7 Accelerator providers are a separate axis

| Backend \| v1 baseline \| Possible optional provider \| What is not
  assumed \|

| --- \| --- \| --- \| --- \|

| llama.cpp \| ARM64 CPU with supported quantized kernels. \| Vulkan or
  another upstream backend if the target driver and build are proven. \|
  A working Wayland/graphics driver does not prove Vulkan compute
  suitability or faster LLM inference. \|

| ONNX Runtime \| CPU EP; test XNNPACK if compiled into the build. \|
  Arm Compute Library / Arm NN where available; other EP only if exact
  target support is proven. \| EP listed upstream does not mean the
  phone vendor NPU is accessible or that all operators execute there. \|

| SonarBird ONNX \| Small CPU inference. \| Validated XNNPACK/ACL/Arm NN
  if useful. \| No need to reserve a phone NPU for a small router unless
  it helps measured latency and power. \|

The ONNX Runtime provider catalogue includes CPU and XNNPACK plus
mobile/edge providers; some ARM-related providers are marked preview.
Select only providers present in the compiled runtime and validated on
Nuxel. \[R6\]

## 5.8 Version and ABI strategy

Pin llama.cpp by immutable git commit and build artifact hash. A model
card requiring "recent llama.cpp" is not a version pin.

Pin ONNX Runtime core and ONNX Runtime GenAI together. Track GenAI C/C++
API/ABI compatibility and rebuild provider add-ons against the exact
core release.

Keep runtime versions in a signed device compatibility manifest, not in
UI source code.

Never hot-update a runtime while a model process is loaded. Stage
update, unload, validate self-test, then switch atomically with
rollback.

# 6. Model packages, compatibility and download cards

## 6.1 The three logical models

| Role \| Current supplied source \| Published GGUF facts from current
  listing \| Primary v1 use \|

| --- \| --- \| --- \| --- \|

| ChatBird \| `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated_GGUF` /
  `Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf` \| HF page shows Llama
  architecture, Q4_K_M about 2.78 GB and metadata page reports 5B
  parameters despite the 4B naming lineage. \| Conversation, general
  explanations, personality-driven chat. \|

| CodeBird \| `empero-ai/Qwen3.8-4B-Distill-GGUF` /
  `Qwen3.8-4B-Q4_K_M.gguf` \| HF GGUF card lists 2.783 GB Q4_K_M, 4B
  model class and Qwen3.5-family hybrid architecture. \| Code
  generation, debugging and extension work; must be benchmarked
  specifically for code tasks. \|

| SonarBird \| Proposed pinned MiniLM-class ONNX encoder plus Nuxel
  routing classifier. \| No exact approved repository/hash/package
  selected in the supplied brief. Do not invent one. \| Lightweight
  intent/route selection in Squad mode. \|

The current ChatBird GGUF listing differs from earlier "4B / Llama 3.1"
shorthand: the GGUF page displays 5B parameters, and its model tree
traces through `Impish_LLAMA_4B` to NVIDIA
Llama-3.1-Minitron-4B-Width-Base. The intermediate fine-tune metadata
identifies the NVIDIA Open Model License; the abliterated fine-tune page
labels itself Llama 3.1 Community License; the GGUF repository metadata
is tagged Apache-2.0. This is a material provenance/license
inconsistency. Preserve every upstream license and obtain a
model-owner/legal determination before redistributing.
\[R7\]\[R8\]\[R9\]

CodeBird is a 4B-parameter distillation into the Qwen3.5-4B
architecture, based on the published Transformers checkpoint. Its own
model card describes reasoning/math/instruction tuning and points to a
9B variant for the strongest code results. Treat CodeBird as the chosen
coding-oriented worker candidate, not as a proven coding benchmark
winner. Benchmark on Nuxel-specific code tasks. \[R10\]

## 6.2 Package variants per model

Each logical model has a registry identity and one or more separately
verified package variants. Do not use the model role or file extension
as the only source of compatibility. Every package records the exact
artifact origin, format, architecture, runtime profile,
tokenizer/template, quantization and hashes.

| Variant \| Contents \| Backend \| Availability rule \|

| --- \| --- \| --- \| --- \|

| ChatBird GGUF \| One GGUF file plus manifest, licence and runtime
  profile. \| llama.cpp \| Can be enabled after immutable revision,
  SHA-256, license and load test are approved. \|

| ChatBird ONNX GenAI \| ONNX graph(s), external tensors, tokenizer,
  genai_config, generation config, export report and manifest. \| ONNX
  Runtime GenAI \| Build from the exact Transformers checkpoint and
  publish only after parity, ARM64 load and licence review. \|

| CodeBird GGUF \| One Q4_K_M GGUF plus manifest and Qwen3.5-compatible
  llama.cpp profile. \| llama.cpp \| Can be enabled after compatible
  llama.cpp build and model card/license validation. \|

| CodeBird ONNX GenAI \| Qwen3.5-family ONNX bundle exported from the
  original Transformers checkpoint; configuration and tokenizer assets.
  \| ONNX Runtime GenAI \| Current architecture tooling makes this
  plausible; exact source/export/provider test remains a gate. \|

| SonarBird ONNX \| Sentence encoder, tokenizer, pooling/normalization
  configuration and classifier head. \| Standard ONNX Runtime \| Not a
  generic MiniLM filename: complete bundle and project classifier must
  be published together. \|

## 6.3 Exact Hugging Face discovery URLs

ChatBird GGUF:
https://huggingface.co/SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated_GGUF/resolve/main/Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf?download=true

CodeBird GGUF:
https://huggingface.co/empero-ai/Qwen3.8-4B-Distill-GGUF/resolve/main/Qwen3.8-4B-Q4_K_M.gguf?download=true

ChatBird Transformers source candidate (for ONNX export):
https://huggingface.co/SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated

CodeBird Transformers source candidate (for ONNX export):
https://huggingface.co/empero-ai/Qwen3.8-4B-Distill

These are discovery/source URLs, not production manifest pins.
Production release metadata must resolve each item to an immutable
repository revision and exact LFS/Xet object hash. Never ship a
`resolve/main` URL as the sole identity of a model release.

## 6.4 The three model cards in NuXtore / PenGuru

| Card \| What the owner sees \| Primary action \|

| --- \| --- \| --- \|

| Download ChatBird \| Role, author/repo, exact file or ONNX package
  variant, size, context, quantization, backend compatibility,
  licence/provenance state, verification status and storage estimate. \|
  Download selected verified package; otherwise show "pending
  verification" and keep action disabled. \|

| Download CodeBird \| Same package details plus Qwen
  architecture/runtime requirement and the fact that code quality must
  be benchmarked. \| Download selected verified package; show
  backend-specific compatibility. \|

| Download SonarBird \| Encoder, tokenizer, pooling/config, classifier
  version, total size, supported labels and local-only status. \|
  Download complete classifier bundle; do not download the sentence
  encoder alone and present it as a working router. \|

Within ChatBird and CodeBird cards, a small `GGUF / ONNX` variant switch
is acceptable when both packages are signed and approved. There are
still three logical model cards, not a separate confusing model for each
runtime.

# 7. SonarBird routing and training pipeline

## 7.1 SonarBird is the decision router, not the answer model

SonarBird is a tiny classifier system, not a generative 0.3--0.6B LLM in
v1. It should run at low cost in Squad mode and produce a constrained
label plus reason. The always-on concept means the service/queue is
available while PenGuru is enabled; it does not mean a microphone or LLM
continuously listens to the environment.

## 7.2 Route labels

| Label \| Definition \| Next step \|

| --- \| --- \| --- \|

| CHAT \| General conversation, explanation, planning or non-code Q&A.
  \| Load ChatBird. \|

| CODE \| Code creation, repair, debugging, completion or extension
  scaffold. \| Load CodeBird; create proposal in a scoped workspace. \|

| SYSTEM \| Explicit supported operation against a Nuxel API. \| Go to
  deterministic typed API through Supervisor and broker; no chat/code
  model required. \|

| ASK \| Ambiguous, conflicting, unsupported or low-confidence request.
  \| Ask the owner a clarifying question; do not load a generative
  worker yet. \|

## 7.3 Tiered pipeline

Request \| +-- Tier 0: deterministic rules (every Squad request) \| -
explicit supported setting + action verb + target id -\> SYSTEM
candidate \| - code fence, stack trace, source file/path, compiler error
-\> CODE candidate \| - high-precision knowledge/chat cues -\> CHAT
candidate \| - conflict or low specificity -\> ASK \| +-- Tier 1: MiniLM
sentence embeddings + Nuxel-trained classifier \| - standard ONNX
Runtime session \| - calibrated class probabilities / confidence \| -
route reason + model version \| +-- Decision policy - clear CHAT/CODE
-\> worker - SYSTEM only when a known typed API maps to a safe action
schema - uncertain / high entropy / disagreement -\> ASK

## 7.4 Routing safety

No `requires_approval` field from SonarBird. Approval is computed by
Supervisor from the action class and capability policy.

Embeddings never execute SYSTEM operations. They may suggest a route; a
separate deterministic action parser and allowlist must resolve exact
operation and parameters.

If a request contains both code and a device action, either split into
explicit subrequests with owner approval or ASK. Do not permit a code
response to smuggle a system action.

Route override is user-only and visible. Override can choose CHAT, CODE
or ASK; SYSTEM must be invoked through its explicit Nuxel UI action.

Log label, scores, confidence bucket, rule ID, classifier version,
override and outcome. Avoid retaining raw prompts by default; if
retained, make it a visible local privacy setting.

## 7.5 Thresholds and training data

Start with conservative thresholds, e.g. \>=0.82 for CHAT/CODE only
after calibration; a mid-confidence band (approximately 0.60--0.82) may
request another signal or ASK; lower confidence -\> ASK. These are
experimental starting points, not universal values. Do not use the
proposed 0.80/0.55 pair as a safety guarantee.

Create a versioned dataset with hundreds of labeled examples per class
to start; include paraphrases, typos, multilingual requests expected in
v1, mixed intent, adversarial prompts and commands quoted in code/logs.

Use a disjoint train/validation/test split by intent family and
conversation source to prevent near-duplicate leakage.

Measure macro-F1, per-class precision/recall, calibration error,
confusion matrix, abstention/ASK rate and SYSTEM false-positive rate.

Freeze a security-oriented test set. Target zero false SYSTEM dispatches
on that set; a wrong CHAT/CODE classification is a UX problem, but an
unauthorized action dispatch is a security failure.

Keep model updates signed and local. Do not automatically train from
private logs or user corrections without a separate opt-in.

## 7.6 SonarBird model package contents

A working SonarBird download is more than `all-MiniLM-L6-v2.onnx`. The
package needs the encoder model, exact tokenizer vocabulary/config,
tokenization behavior, mean-pooling configuration, normalization
settings if used, classifier weights/label map, confidence calibration
data, package metadata, licences and hashes. The project should either
export the classifier head into the ONNX graph or ship an audited small
native classifier implementation with the precise transform version.

# 8. Model Manager, scheduler and persistent queue

## 8.1 Process model

| Process \| Lifetime \| Responsibility \|

| --- \| --- \| --- \|

| `nuxel-penguru` \| Only while feature enabled and an active
  session/owner policy requires it. \| Mode, queue, routing
  orchestration, UI API and local state. \|

| SonarBird inference component \| Loaded only in Squad mode; small ONNX
  session may remain resident while Squad is active. \| Run Tier 1
  classification after Tier 0. \|

| `nuxel-ai-worker` \| Demand-loaded for ChatBird or CodeBird; one heavy
  decoder process resident by default. \| Run selected model with
  selected runtime; no broker credentials or general network. \|

| Download helper \| Short-lived, started only after foreground user
  download action. \| HTTPS transfer, resume, signature/hash checks,
  atomic install. \|

| Supervisor/test runner \| On request for proposal validation or tests.
  \| Sandboxed workspace, bounded test profile, approval package. \|

## 8.2 State machine

| State \| Meaning \| Allowed transition \|

| --- \| --- \| --- \|

| DISABLED \| PenGuru OFF; no model, classifier or PenGuru daemon
  running. \| Enable -\> IDLE. \|

| IDLE \| Control plane enabled; no generative worker loaded. \| Request
  -\> ROUTING / LOADING. \|

| ROUTING \| Tier 0/1 classification in Squad mode. \| CHAT/CODE -\>
  LOADING; SYSTEM -\> SUPERVISOR; ASK -\> WAITING_USER. \|

| LOADING(model, engine) \| Verify model manifest, runtime, provider,
  RAM and thermals; start worker. \| Success -\> ACTIVE; failure -\>
  ERROR or IDLE. \|

| ACTIVE(model) \| Worker is handling a bounded request or waiting
  inside idle timeout. \| Completion -\> ACTIVE/IDLE; switch -\>
  DRAINING. \|

| DRAINING / CANCELLING \| Stop new work for old worker; finish/cancel
  bounded generation. \| UNLOADING. \|

| UNLOADING \| Terminate worker, release context/cache, verify memory
  reclaim. \| IDLE or LOADING(next). \|

| ERROR \| Load/inference failed; record typed failure and avoid restart
  loop. \| Manual retry or bounded retry -\> IDLE. \|

## 8.3 One-heavy-model policy

Default: one generative worker resident at a time, irrespective of
whether it uses llama.cpp or ONNX Runtime GenAI. SonarBird classifier is
lightweight and may coexist with a worker in Squad mode. Keep-warm mode
is off by default and requires explicit memory budget. Do not load
ChatBird and CodeBird simultaneously on the target phones unless a
future measured device profile specifically allows it.

## 8.4 Memory budget model

usable_for_worker = total_RAM - measured_os_and_compositor_reserve -
foreground_app_reserve - NuXAI_service_overhead -
SonarBird_overhead_if_Squad - safety_margin

worker_peak = weights_or_onnx_tensors + runtime_compute_buffers +
KV_cache(context, batch, precision) + tokenizer / prompt / logits
buffers + provider allocations

load only if worker_peak \<= usable_for_worker

Model file size is not model runtime RAM. KV cache grows with context
and can become a substantial part of memory. Use measured peak RSS/PSS
and allocator/provider metrics. An ONNX artifact may have a different
runtime footprint from its GGUF counterpart, even where both derive from
the same source checkpoint.

## 8.5 Resource scheduler

Probe free memory at load time and periodically during generation;
include a reserve for the UI/compositor and system daemons.

Apply context limits per device/model/backend profile. Start with
conservative contexts such as 4K and raise only from measurement.

Limit worker threads and batch size to protect interactive
responsiveness. Tune per CPU topology; do not hard-code "4 threads" for
every device.

Honor battery-saver and thermal states; pause/decline long generation
when device health is outside tested range.

On memory pressure, cancel generation, unload the worker and return a
clear status. Do not rely on swap-to-disk as a default mobile strategy.

Expose cold-load time, warm-load time, time-to-first-token, prompt
tokens/s, decode tokens/s, peak memory and provider fallback to the UI.

# 9. NuXAI service architecture and Nuxel integration

## 9.1 Proposed service layout

services/nuxel-penguru/ daemon/ \# D-Bus service, mode controller, queue
supervisor/ \# typed actions, approval hash, rollback runtime/ common/
\# stable InferenceRuntime contract llama_cpp/ \# GGUF adapter and
pinned libllama build onnx_genai/ \# ONNX Runtime GenAI adapter
ort_session/ \# standard ORT sessions for SonarBird models/ \# model
registry + signed manifests downloads/ \# resumable downloader and
installer scheduler/ \# RAM, thermal, battery and worker lifecycle
schemas/ \# versioned request/route/action schemas tests/ systemd/

pwa/nuxel-apps/penguru/ index.html / app source manifest.json assets/
tests/

var/lib/nuxel-penguru/ queue.db conversations/ \# policy-controlled and
owner-deletable models/ \# immutable package store workspaces/ \#
isolated feature/code workspaces audit/ staging/ \# not trusted until
verified

## 9.2 Service identity and IPC

Proposed D-Bus well-known name: `org.nuxel.PenGuru` (or a versioned
interface such as `org.nuxel.PenGuru1`). Run the main control plane as a
dedicated unprivileged service account. Use D-Bus peer credentials and
Nuxel session/launcher identity to authenticate clients. The UI must not
be issued broker secrets. Runtime workers receive only the minimum
prompt/model/workspace data needed for one job.

## 9.3 Systemd hardening profile

\[Service\] User=nuxel-penguru Group=nuxel-penguru NoNewPrivileges=true
PrivateTmp=true ProtectSystem=strict ProtectHome=read-only
ProtectKernelTunables=true ProtectKernelModules=true
ProtectControlGroups=true LockPersonality=true RestrictSUIDSGID=true \#
Writable paths limited to PenGuru state and model store.
ReadWritePaths=/var/lib/nuxel-penguru \# Restrict address families to
local IPC unless a separate downloader is active.
RestrictAddressFamilies=AF_UNIX \# Add MemoryMax/CPUQuota/TasksMax after
device measurements.

This is a starting profile, not a production unit file. Validate every
directive against the actual systemd version and kernel on Nuxel. A
separate short-lived downloader may receive HTTPS network access; the
inference worker should not. Do not use a container name as proof of
isolation.

## 9.4 Application and asset pipeline

Add a unique PenGuru app entry to `pwa/nuxel-common/app-registry.json`
and a manifest built through the existing PWA asset pipeline.

Reuse `pwa/nuxel-common/bridge.js` and `bridge-version.json`; validate
schema changes in CI.

Use session and notification services for owner-facing approvals/status
only after the caller identity model is hardened.

Use `penguinterface` as read-only UX reference and `rootcontrol` only as
a reference for privilege boundaries, not as PenGuru execution API.

Add build tests proving model manifest schema, service unit hardening,
runtime artifact compatibility and route/action schemas are packaged.

## 9.5 PenGuru Control Center

| Panel \| Required state / controls \|

| --- \| --- \|

| Overview \| Feature enabled, selected mode, selected runtime, active
  model, active provider, queue depth, offline status and device health.
  \|

| Model Library \| Three logical model cards; package format/backend
  selector; provenance, hash, licence, size, storage, download/delete.
  \|

| Runtime \| llama.cpp and ORT GenAI toggles; runtime versions,
  CPU/provider profile, threads, context and diagnostics. \|

| Squad routing \| SonarBird enabled in Squad mode, route
  reason/confidence, ASK flow and temporary route override. \|

| Approvals \| Exact proposed changes, changed files/settings,
  capabilities, tests, risk, approval expiry and rollback. \|

| Privacy \| Local retention, clear conversation, delete model, network
  state, voice status and any future LAN pairing. \|

| Diagnostics \| Benchmark profile, current memory use, thermal
  warnings, backend logs with secrets and prompt text redacted. \|

# 10. Supervisor, security and capability model

## 10.1 Trust zones

| Zone \| Contents \| Policy \|

| --- \| --- \| --- \|

| Untrusted data \| User text, model replies, code, repo files, logs,
  web pages, app notifications and model cards. \| Treat as data;
  instruction-like text cannot change policy. \|

| Model workers \| SonarBird, ChatBird, CodeBird and runtime libraries.
  \| No root, broker token, general network, system write path or
  arbitrary shell. \|

| NuXAI control plane \| Queue, model manager, route policy and
  Supervisor orchestration. \| Unprivileged, schema-validated state
  machine, minimal filesystem access. \|

| Permission authority \| nuxel-permd, portal and typed bridge adapter.
  \| Canonical capability registry, authenticated identity, explicit
  grant and audit. \|

| Privileged host APIs \| Settings, radio, service, package and
  extension providers. \| Dedicated trusted services; only allowlisted
  typed operations. \|

## 10.2 Action protocol

Model produces a proposed action object; no shell string. Example shape:
action name plus typed args, validated against a fixed schema.

Supervisor resolves the operation against a compiled allowlist and
canonical capability registry. Unknown action -\> deny.

Supervisor creates an immutable preview with canonical payload, affected
resources, capability, risk tier, tests and rollback plan.

Owner approval is stored against a cryptographic hash of that exact
payload, target device/session, capability and expiry.

Before execution, the trusted broker verifies caller identity,
user/session, action hash, current policy, grant scope, expiry and
target again.

Any payload change invalidates approval. Retry/replay with a different
target or app identity is rejected.

Execution result and rollback reference are logged. The model never
receives the broker secret or the power to approve its own proposal.

## 10.3 Risk tiers

| Tier \| Examples \| Default v1 policy \|

| --- \| --- \| --- \|

| Read-only \| Battery level, device identity, service status,
  documented diagnostics. \| Allowed only via authenticated typed
  capability; log access. No free-form shell. \|

| Reversible \| Set normal user preference, create a schedule, change a
  supported radio state. \| Preview and explicit per-action confirmation
  unless narrow owner policy grants otherwise. \|

| Persistent write \| Install extension, change service, write system
  configuration or package. \| Staged test, exact diff, explicit portal
  approval, audit and verified rollback required. \|

| Destructive / boot-critical \| Format disk, flash partition, modify
  boot chain/kernel/driver, root password or sudoers. \| Not supported
  by PenGuru v1; reject and explain. \|

## 10.4 Code execution and extension builder

CodeBird may write into a disposable workspace only. The test runner
must be a separate process/service with explicit resource limits,
read-only source dependencies where practical, no network by default, a
dedicated UID, seccomp and only those namespace/systemd restrictions
proven on the active kernel. Use a disposable worktree or snapshot and
block symlink/path traversal outside the workspace.

If effective isolation cannot be proven on the device, do not execute
generated code. Return a patch or downloadable artifact for review on a
trusted development machine.

Run a fixed command catalogue (for example, project-defined lint/unit
test/build targets), not arbitrary model-supplied shell.

Limit CPU time, memory, process count, file count, output size and wall
time. Kill on limit breach and preserve logs safely.

Install only after the owner sees file diff, manifest, declared
permissions, test evidence and rollback path.

Rollback is only promised where a tested transaction/snapshot mechanism
exists. Never imply every system action is automatically reversible.

## 10.5 Prompt injection and supply-chain defence

Prompt-injection text in a repository, model card, log, web page or
notification is still untrusted input. Use explicit source labels,
isolate context, escape control tokens where appropriate, and do not let
retrieved content alter tool policy. The Supervisor/broker remains the
security boundary even if ChatBird is abliterated or any model returns
malformed content.

# 11. Download, update and integrity pipeline

## 11.1 Download state machine

NOT_INSTALLED -\> USER_CONFIRMED -\> CHECK_SPACE -\> DOWNLOADING -\>
VERIFY_SIGNATURE -\> VERIFY_HASHES -\> VERIFY_FORMAT -\>
VERIFY_LICENSE_ACK -\> ATOMIC_INSTALL -\> SELF_TEST -\> READY Any
failure -\> QUARANTINE / CLEAN_PARTIAL -\> ERROR

## 11.2 Required behaviour

Show exact repository, immutable revision/commit, file list, sizes,
package format, backend compatibility, device requirements and license
notice before download.

Check free storage for download, temporary partial file, ONNX external
tensor shards, extraction/staging overhead and future updates. Reserve
safety space.

Use HTTPS, resumable range requests where supported, cancellation,
retry/backoff and clear network errors.

Write into a temporary location. Verify a signed manifest distributed
through a trusted Nuxel release channel; do not fetch a hash from the
same untrusted model host and treat it as a trust anchor.

Check SHA-256 for every file, package signature, GGUF or ONNX metadata,
architecture, tokenizer assets, size and manifest version.

Only then atomically move into immutable
`/var/lib/nuxel-penguru/models/<model-id>/<revision>/<variant>/` and
mark READY.

Keep last known-good runtime/model package during updates. Delete
partial/corrupt downloads and provide owner-controlled removal.

Keep license notices and accepted revision records accessible to the
owner.

## 11.3 Manifest example

{ "schema_version": 1, "model_id": "codebird", "variant_id":
"qwen38-4b-q4km-gguf", "source_repo":
"empero-ai/Qwen3.8-4B-Distill-GGUF", "source_revision":
"`<immutable-commit-sha>`{=html}", "files": \[{"path":
"Qwen3.8-4B-Q4_K_M.gguf", "size_bytes": "`<exact-byte-count>`{=html}",
"sha256": "`<release-verified-sha256>`{=html}"}\], "format": "GGUF",
"architecture": "qwen35", "quantization": "Q4_K_M", "runtime":
{"engine": "llama.cpp", "min_commit": "`<tested-commit>`{=html}"},
"license": {"spdx": "Apache-2.0", "notice_file": "LICENSE"},
"signature": "`<detached-signature-reference>`{=html}" }

The values in angle brackets are intentionally placeholders. Do not
invent hashes, immutable commits or exact file sizes. The signed release
manifest is populated only after the release pipeline downloads the
chosen revision and independently hashes the bytes.

## 11.4 Runtime package variants are separate downloads

If llama.cpp is selected, the model card requests the GGUF variant. If
ONNX Runtime GenAI is selected, the card requests the separate ONNX
package. If the ONNX package has not passed export and device tests,
disable that variant and explain the blocker. Never claim that a GGUF
download contains ONNX assets.

# 12. Devices, memory, acceleration and power

## 12.1 Target-device policy

| Device \| Known/claimed platform details \| PenGuru position \|
  Release gate \|

| --- \| --- \| --- \| --- \|

| Pixel 10 Pro XL \| Project target claims 16 GB RAM and Tensor G5. \|
  Primary full target. Test one 4B/5B-class worker at a time under
  native Nuxel. \| Verify exact SKU, kernel, boot chain, memory
  availability, CPU perf, provider access and sustained thermal results.
  \|

| Galaxy S10+ Exynos \| Exynos 9820; 8 GB and some 12 GB variants. \|
  Secondary, conditional. CPU-first. Single GGUF/ONNX worker only if
  memory/heat test passes. \| Exact regional/SKU; the Nuxel environment
  may have a Linux 4.14.253 baseline and sandbox gaps. \|

| Moto G7 Power \| Snapdragon 632; variants may differ in memory (3 GB /
  4 GB). \| UI and deterministic control first. Do not promise current
  ChatBird or CodeBird local inference. \| Identify exact RAM and
  storage variant; consider a separate smaller model profile later. \|

The earlier plan treated Android + Termux/proot/chroot as the v1 hosting
assumption. The NuXAI brainstorm identifies the architectural
opportunity in native Nuxel: llama.cpp and ONNX Runtime can run in
native Fedora ARM64 userland without inheriting Android's application AI
architecture. A proot environment can support experiments, but it is not
equivalent to native systemd, D-Bus, Wayland integration or device-level
security. Do not treat it as the production integration target.

## 12.2 ARM CPU baseline

Compile for ARM64 with baseline CPU kernels supported by the real
target; test NEON and any optional ARM optimizations in reproducible
builds.

Use configurable thread count and CPU affinity, then measure latency and
UI responsiveness. Avoid occupying all big cores during interactive UI
work.

Benchmark prompt processing and token generation separately. The model
may behave differently across llama.cpp and ORT GenAI even from
identical source weights.

Run both backends in CPU mode first. Hardware-provider work begins only
after correct inference and memory budgeting are established.

## 12.3 GPU path

For llama.cpp, evaluate Vulkan only where the device has a compatible
userspace driver and compute support. A working graphics stack does not
prove relevant model operations are supported or faster. For ONNX
Runtime, test only execution providers built into the shipped ARM64
runtime. Record operator fallback and whether the graph executes on the
provider or falls back to CPU. Compare energy per generated token, not
only peak throughput.

## 12.4 NPU path

NPU acceleration remains exploratory. The hardware may exist, but vendor
firmware, driver interfaces, runtime operators and kernel integration
determine whether third-party Linux processes can use it. Do not assume
Tensor G5 or Exynos neural hardware is exposed to native Fedora. Make
the provider discoverable and optional only after a real end-to-end
model test.

## 12.5 Measurement protocol

Identify device SKU, RAM, storage, kernel, OS build, CPU topology,
runtime commit, provider and model revision.

Run at least three cold starts per model/runtime and several warm
requests; record time-to-load and time-to-first-token.

Measure prompt tokens/s and decode tokens/s at fixed
prompt/context/output lengths; record peak and steady RSS/PSS and
provider allocations where available.

Run short and sustained loads; record temperature, throttling state,
battery percentage or power if measurable, and foreground UI frame
responsiveness.

Repeat under low-memory conditions and with another foreground app
active. Test cancellation and unload/reload loops.

Publish raw logs and scripts. Do not place guessed tokens-per-second
figures in release notes.

## 12.6 Device profiles

Store a compatibility profile per exact device SKU and Nuxel build. It
includes runtime commits, tested model variants, provider list, safe
thread/context defaults, memory reserve, thermal thresholds, minimum
storage and sandbox feature set. The UI shows "supported",
"experimental" or "not supported" based on that profile.

# 13. Voice, privacy and network policy

## 13.1 Voice roadmap

The architecture can add a voice pipeline later: push-to-talk or
explicit wake-word activation -\> local speaker confirmation if needed
-\> local STT -\> request queue -\> SonarBird or selected worker -\>
local TTS. A wake-word model is not SonarBird; STT is not a generative
LLM.

V1 is text-first; microphone permission is off by default and no
wake-word process runs at boot.

Later voice mode requires foreground activation, visible microphone
indicator, explicit permission, local processing and an immediate stop
control.

Never silently record ambient audio. Provide push-to-talk as the default
voice UX until wake-word power/privacy costs are proven.

Speaker verification is not a substitute for action approval; it may
contribute to session assurance but cannot itself authorize privileged
changes.

## 13.2 Privacy and retention

Prompts, model outputs, embeddings, routing traces and queue records
stay local by default.

No analytics, crash upload or prompt telemetry unless the owner
separately opts into a clearly described feature.

Provide per-conversation deletion, clear-all, retention duration and
local audit log controls.

Redact auth tokens, personal paths and secrets from diagnostics. Prefer
aggregate routing metrics over raw prompt content.

Worker network access is denied by default. Downloads use a separate,
user-started downloader process.

## 13.3 Future LAN inference

A remote M1 Max or LAN inference server can be a future
`RemoteRuntimeProvider`, but it is not part of default v1. It needs
explicit pairing, authenticated transport, key rotation, server
identity, allowlisted network destination, privacy warnings, per-request
consent and local fallback. The UI must show when a prompt leaves the
phone. There is no automatic cloud fallback.

# 14. API contracts and configuration examples

## 14.1 Request envelope

{ "schema_version": 1, "request_id": "uuid", "conversation_id": "uuid",
"mode": "squad", "text": "Fix this extension traceback", "workspace_id":
"optional-id", "attachments": \[{"kind": "file_ref", "id":
"scoped-file-id"}\], "runtime_preference": "auto", "client_context":
{"app_id": "resolved-by-auth-layer", "session_id":
"resolved-by-auth-layer"} }

The UI does not get to assert its own trusted app identity in the
request body. The identity shown above is resolved by the service from
authenticated D-Bus/launcher/session credentials and attached to
internal request state.

## 14.2 Route response

{ "schema_version": 1, "request_id": "uuid", "route": "CODE",
"confidence": 0.91, "reason_code": "STACK_TRACE_AND_SOURCE_FILE",
"router_version": "sonarbird-route-`<revision>`{=html}", "worker":
"codebird", "runtime": "llama.cpp", "provider": "CPU",
"override_available": true }

No `requires_approval` field belongs in this object. The route result
selects a worker only; authorization is separate deterministic state.

## 14.3 Proposed D-Bus methods

| Method \| Inputs / outputs \| Rule \|

| --- \| --- \| --- \|

| GetStatus \| Mode, enabled flag, state, active model/backend/provider,
  queue depth, device profile. \| Read-only, app/session scoped. \|

| SetEnabled \| Owner-authorized boolean. \| Enables/disables service;
  no model starts until explicitly requested. \|

| SetMode \| `chatbird \| codebird \| squad`. \| Serialized mode change;
  model availability checked before switch. \|

| SetRuntimePreference \| `auto \| llama_cpp \| ort_genai` plus optional
  model override. \| Reject if incompatible; return reason, no silent
  fallback. \|

| SubmitRequest \| Validated request envelope. \| Bound payload size,
  queue depth, session ownership and rate limits. \|

| GetRequest / CancelRequest \| Request ID. \| Only caller/session that
  owns request may query/cancel, subject to owner admin policy. \|

| OverrideRoute \| Request ID + CHAT/CODE/ASK. \| Owner action only; no
  free-form SYSTEM override. \|

| ListModels / StartDownload / CancelDownload / DeleteModel \| Model ID
  and selected verified variant. \| Download starts only after
  foreground user action and licence acceptance. \|

| ListApprovals / DecideApproval \| Approval ID + approve/deny. \|
  Approval bound to payload hash, target, capability, user session and
  expiry. \|

| RollbackAction \| Action ID. \| Only if a verified rollback reference
  exists; explicit confirmation. \|

| GetDiagnostics \| Read-only diagnostic scope. \| Redact prompt
  content, auth data and private paths by default. \|

## 14.4 Example runtime configuration

\[penguru\] enabled = false mode = "squad"

\[runtime\] preferred = "auto" enable_llama_cpp = true enable_ort_genai
= true max_heavy_workers = 1 idle_unload_seconds = 120

\[sonarbird\] enabled_in_squad = true engine = "onnxruntime"
low_confidence_action = "ask"

\[models.chatbird\] default_variant = "gguf-q4km" preferred_engine =
"llama_cpp" context_limit = 4096

\[models.codebird\] default_variant = "gguf-q4km" preferred_engine =
"llama_cpp" context_limit = 4096

\[privacy\] network_for_workers = false raw_prompt_routing_logs = false

Configuration is user preference, not authority. Capability grants and
action approvals are stored by the canonical permission subsystem, not
in this config file.

# 15. Testing, acceptance criteria and release evidence

## 15.1 Test matrix

| Area \| Required tests \|

| --- \| --- \|

| Model artifacts \| Signature, revision pin, SHA-256, file sizes,
  GGUF/ONNX metadata, tokenizer/config completeness, licence notices,
  corrupt/partial download, wrong architecture. \|

| llama.cpp \| ARM64 build, both GGUF models load, Qwen3.5/Gated
  DeltaNet load, correct chat templates, cancellation, OOM recovery, no
  external TCP listener. \|

| ONNX Runtime GenAI \| ARM64 package/ABI, both exact ONNX exports,
  graph/provider compatibility, tokenizer/template parity, KV-cache
  behaviour, generation output and cancellation. \|

| SonarBird \| Tier 0 rules, Tier 1 classifier
  precision/recall/calibration, zero false SYSTEM on frozen security
  set, confidence/ASK and override. \|

| Modes \| Single ChatBird bypasses router; Single CodeBird bypasses
  router; Squad routes all labels; queued mode switches behave
  deterministically. \|

| Runtime selector \| GGUF + llama.cpp pass; ONNX + ORT GenAI pass;
  incompatible pair rejected; Auto shows actual backend; no silent
  conversion/fallback. \|

| Supervisor \| Malformed JSON, schema fuzzing, path traversal, symlink
  attacks, oversized output, approval hash tamper, replay and denied
  capability. \|

| Permissions \| Forged app ID, expiry, one-shot replay, session grant
  expiry, portal timeout, bridge down, unknown capability and
  revocation. \|

| Sandbox \| Host-path access, network, device nodes, fork bomb, memory
  exhaustion, special files and writes outside workspace. \|

| Privacy/offline \| Airplane-mode inference after install, no worker
  network, no telemetry, deletion, retention and log redaction. \|

| Device health \| Cold/warm load, peak RSS/PSS, TTFT, prompt/decode
  speed, thermals, battery, UI responsiveness, suspend/resume and leak
  test. \|

| Rollback \| Extension rollback and each supported settings/system
  action restore correctly after simulated failure. \|

## 15.2 Acceptance criteria

PenGuru defaults OFF; OFF stops PenGuru service, classifier and model
workers and releases memory.

All three user modes work offline after their model package has been
installed.

Single modes bypass SonarBird; Squad mode uses SonarBird and visibly
explains route decisions.

Owner can select Auto, llama.cpp or ONNX Runtime GenAI. Unsupported
model/backend pairings fail with an actionable status and never silently
switch.

One heavyweight model is resident by default. Worker load/unload and
cancellation do not leak significant memory over repeated cycles.

All model packages match a signed immutable manifest and have known
licence notices/provenance.

No model output can execute a system action without the typed
Supervisor/broker/portal path.

No false SYSTEM dispatch occurs in the frozen adversarial route set;
uncertain requests ASK.

Every supported write has a tested rollback or is explicitly described
as non-reversible and excluded.

Performance and power claims are tied to a named
device/SKU/OS/runtime/model test record.

## 15.3 Benchmark record format

{ "device_sku": "`<exact-sku>`{=html}", "nuxel_build":
"`<commit-or-image-id>`{=html}", "kernel": "\<uname -r\>", "runtime":
{"engine": "llama_cpp", "version": "`<commit>`{=html}", "provider":
"CPU"}, "model": {"id": "codebird", "revision": "`<sha>`{=html}",
"variant": "gguf-q4km"}, "context_tokens": 4096, "prompt_tokens": 512,
"generated_tokens": 128, "cold_load_ms": 0, "time_to_first_token_ms": 0,
"prompt_tokens_per_second": 0.0, "decode_tokens_per_second": 0.0,
"peak_rss_bytes": 0, "peak_temperature_c": 0.0, "battery_delta_percent":
0.0, "result": "pass\|fail", "log_sha256": "`<hash>`{=html}" }

# 16. Phased implementation roadmap

| Phase \| Work packages \| Exit gate \|

| --- \| --- \| --- \|

| 0 --- Security and design freeze \| Fix bridge dev-mode authentication
  and app identity binding; repair grant cache once/session semantics;
  canonical capability mapping; confirm target image/kernel; establish
  service and app IDs. \| P0/P1 tests pass; PenGuru remains chat-only
  until then. \|

| 1 --- Dual-runtime spike \| Build/pin llama.cpp ARM64; load
  ChatBird/CodeBird GGUF; build/pin ONNX Runtime + GenAI ARM64; export
  candidate ONNX packages from original checkpoints; run SonarBird ONNX.
  \| Exact GGUF load tests pass; ONNX exports either pass or are clearly
  recorded as unavailable; device memory baselines captured. \|

| 2 --- NuXAI platform core \| Implement D-Bus service, mode controller,
  queue, model registry, scheduler, runtime interface, llama.cpp
  adapter, ORT GenAI adapter and standard ORT SonarBird session. \| Same
  API drives both backends; incompatible package/runtime pairing
  rejected. \|

| 3 --- Model Store + single modes \| Three model cards, downloader,
  signed manifests, package variants; Single ChatBird and Single
  CodeBird end-to-end; chat UI, status and cancellation. \| Both single
  modes work offline and bypass SonarBird; hashes verified; one-worker
  policy reliable. \|

| 4 --- SonarBird + Squad \| Tier 0 rules, MiniLM embeddings and Nuxel
  classifier; training/evaluation; route reason, confidence, ASK and
  override. \| Routing thresholds calibrated; zero false SYSTEM dispatch
  in frozen security set; mode behaviour verified. \|

| 5 --- Read-only broker tools \| Typed system inspection, authenticated
  identity, canonical capabilities, portal approvals and audit UI. \|
  Read-only device status is reliable; P0/P1 security paths remain
  closed. \|

| 6 --- Safe writes + extension builder \| Scoped file workspaces, patch
  generation, fixed test runner, diff/manifest previews, owner approval,
  staged install and rollback. \| Only supported operations can write;
  isolation verified on target kernel; rollback succeeds. \|

| 7 --- Hardening and pilot \| Thermal/battery tuning, offline/privacy,
  adversarial tests, accessibility, packaging, signatures,
  update/rollback and release docs. \| Opt-in pilot on primary device;
  secondary devices enabled only after exact profiles pass. \|

## 16.1 Recommended engineering order

Build one runtime end-to-end before making two engines work in parallel.
Recommended order: (1) common API contract and model registry, (2)
llama.cpp GGUF path for both supplied files, (3) SonarBird standard ONNX
path, (4) ONNX Runtime GenAI export for CodeBird then ChatBird, (5)
UI/runtime toggles and compatibility matrix. This is sequencing
discipline, not a product limitation.

# 17. Risks, design choices and launch checklist

| Risk / open question \| Impact \| Mitigation / decision \|

| --- \| --- \| --- \|

| GGUF is not ONNX \| Owner selects ORT but only GGUF package exists. \|
  Separate artifact variants; publish ONNX only from source checkpoints
  and after tests; no implicit conversion. \|

| ORT GenAI API maturity \| The Generate API docs mark it Preview and
  subject to change. \| Versioned adapter, pinned ABI, automated
  conformance tests and llama.cpp fallback only when user allows Auto.
  \|

| ChatBird license/provenance conflict \| GGUF tag, abliterated
  fine-tune card and intermediate NVIDIA base metadata are inconsistent.
  \| Do not redistribute until upstream rights, license chain and model
  author statements are reviewed. \|

| CodeBird 4B code quality \| Reasoning distill card emphasizes
  math/reasoning/instruction; model card notes a 9B variant for stronger
  code performance. \| Benchmark Nuxel tasks and code evaluations; keep
  option to replace model later without changing architecture. \|

| ARM provider availability \| GPU/NPU provider may be unavailable or
  slower than CPU. \| CPU-first; discover provider at runtime; benchmark
  power and latency; never assume NPU. \|

| S10+ memory/kernel \| 8 GB variant, old kernel, limited sandbox
  features and thermal constraints. \| Exact SKU matrix; short context;
  one model; disable code runner if isolation or RAM fails. \|

| Moto G7 Power \| 3/4 GB variants make 4B inference unrealistic. \|
  Control-plane/UI support first; smaller model profile is a separate
  future decision. \|

| Permission path bypass \| Bridge dev mode and once/session cache bug.
  \| G0 blockers and tests; no privileged PenGuru actions earlier. \|

| Prompt injection / unsafe generated code \| Model might follow hostile
  content or produce unsafe patch. \| Untrusted-data handling, typed
  tools, worker sandbox, action hash, approval and rollback. \|

| Model package supply chain \| Mutable `main` branch and host-provided
  hashes are insufficient. \| Immutable revisions, signed release
  manifest, SHA-256 and atomic install. \|

## 17.1 Decisions to make before Phase 1 exits

Which exact Nuxel image/kernel is the initial native target, and which
phone SKU is the first supported build?

Will ChatBird be offered as default or marked as an explicitly chosen
low-refusal personality model? The deterministic Supervisor remains the
safety boundary either way.

Who signs model manifests and which release key trust root is embedded
in Nuxel?

What ONNX export precision and target provider should be the first
published package for each model?

What context and battery/thermal budget define a "supported" phone
profile?

Is the remote LAN provider reserved for v2? Recommendation: yes, keep v1
fully local.

## 17.2 Launch checklist

P0 bridge identity weakness fixed; production dev bypass impossible.

Once/session grant cache semantics fixed and tested through actual
bridge API.

Capability registry canonicalized; no fourth policy source.

Runtime abstraction and mode controller implemented with strict package
compatibility.

ChatBird and CodeBird GGUF packages pinned and tested under llama.cpp.

Any ChatBird/CodeBird ONNX package separately exported, hashed and
tested under ONNX Runtime GenAI.

SonarBird complete ONNX package and classifier evaluation signed off.

Downloads verify signed manifests and remove/restore partial or corrupt
files safely.

All three modes and runtime toggle tested offline.

No model has privileged credentials, arbitrary shell access or approval
capability.

Kernel sandbox and rollback mechanisms verified on target device, not
inferred from container labels.

User-facing documentation states exact supported devices, runtimes and
limitations.

# Appendix A. Proposed repository layout

services/nuxel-penguru/ daemon/ main.cpp\|main.rs\|main.py \# choose
Nuxel-standard implementation language dbus-service.* mode-controller.*
request-queue.\* runtime/ api/ \# common request/stream contracts
llama-cpp/ \# pinned GGUF adapter onnxruntime/ \# standard ONNX session
adapter onnxruntime-genai/ \# LLM generation adapter sonarbird/ rules/
classifier/ labels.json calibration.json supervisor/ schemas/ workspace/
runner/ approvals/ rollback/ model-store/ registry.schema.json
manifests/ downloader/ scheduler/ systemd/ tests/

pwa/nuxel-apps/penguru/ pwa/nuxel-common/bridge.js \# reuse existing
pwa/nuxel-common/bridge-version.json pwa/nuxel-common/app-registry.json
\# add PenGuru app entry

Keep package binaries and model weights out of the source repository.
Source contains manifests, build recipes, signatures/public keys,
schemas and tests. Large artifacts are downloaded through the signed
model store.

# Appendix B. External technical references

The following upstream pages were checked on 9 November 2026. They are
technical references, not blanket compatibility guarantees for Nuxel
phones.

\[R1\] llama.cpp upstream repository and README: GGUF inference, CPU and
supported backend overview. https://github.com/ggml-org/llama.cpp

\[R2\] llama.cpp server API, structured output, function calling and
local server options. Use as development reference; production should
expose only NuXAI APIs.
https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

\[R3\] ONNX Runtime Generate API documentation. It describes
tokenization, preprocessing, inference, logits, sampling and KV-cache
management; page marks API Preview. https://onnxruntime.ai/docs/genai/

\[R4\] ONNX Runtime GenAI release page. At research time v0.17.0 was
listed latest; Linux ARM64 assets and current model/runtime changes are
documented. https://github.com/microsoft/onnxruntime-genai/releases

\[R5\] ONNX Runtime GenAI model-builder support and Qwen3.5/3.8 export
configuration details.
https://github.com/microsoft/onnxruntime-genai/blob/main/src/python/py/models/README.md

\[R6\] ONNX Runtime Execution Provider catalogue; provider presence,
release status and platform targets.
https://onnxruntime.ai/docs/execution-providers/

\[R7\] ChatBird GGUF repository: architecture, Q4_K_M size display,
model tree and GGUF metadata.
https://huggingface.co/SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated_GGUF

\[R8\] ChatBird Transformers fine-tune card, claimed
architecture/parameters/context and `llama3.1` licence metadata.
https://huggingface.co/SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated

\[R9\] NVIDIA base model card and NVIDIA Open Model License. Review with
intermediate fine-tune provenance.
https://huggingface.co/nvidia/Llama-3.1-Minitron-4B-Width-Base

\[R10\] CodeBird Transformers source checkpoint, Qwen3.5 architecture,
4B model class, native context, distillation scope and Apache-2.0
statement. https://huggingface.co/empero-ai/Qwen3.8-4B-Distill

\[R11\] CodeBird GGUF repository, Q4_K_M file size, Qwen3.5/Gated
DeltaNet note and llama.cpp usage guidance.
https://huggingface.co/empero-ai/Qwen3.8-4B-Distill-GGUF

\[R12\] Intermediate ChatBird fine-tune model card metadata identifying
the NVIDIA Open Model License.
https://huggingface.co/SicariusSicariiStuff/Impish_LLAMA_4B

# Final recommendation

Build PenGuru as a first-class Nuxel service, not an app-specific
wrapper around one runtime. Keep mode selection (ChatBird / CodeBird /
Squad), generative runtime selection (llama.cpp / ONNX Runtime GenAI)
and hardware provider selection independent. This preserves the owner's
choice while accurately exposing compatibility limits.

For the first useful release, get both selected GGUF models working with
a pinned llama.cpp build, implement SonarBird as a complete standard-ORT
ONNX classifier, and finish the common runtime/model interface. Then
publish ONNX GenAI variants from the original Transformers checkpoints
and enable the ONNX runtime toggle per model only when export,
correctness, memory and ARM64 tests pass.

| The architecture in one line SonarBird routes; ChatBird and CodeBird
  answer; llama.cpp and ONNX Runtime GenAI are interchangeable only
  where model packages are compatible; NuXAI manages resources;
  Supervisor validates; Nuxel permission services authorize; the owner
  decides. \|

| --- \|
