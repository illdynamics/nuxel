I think PenGuru could become one of Nuxel's most distinctive features. 🐧🔥

Not simply because you'd have an LLM running on a Linux phone—that's already possible elsewhere—but because of what you're proposing:

An optional, fully local AI that understands its own operating system, can operate it on your behalf, and can propose, build, test and install new functionality with your permission.

That last part is especially interesting. You're essentially describing a personal operating-system engineer living inside the phone.

# 🐧 PenGuru — Your phone's own Linux engineer

## PenGuru

Local Intelligence Engine for Nuxel

Opt-in · Local-first · User-controlled

"Your phone. Your intelligence. Your rules."

Offline by default

No cloud account needed

Private

Chats and actions remain local

System-aware

Diagnose and extend Nuxel

Permission-based

You approve what it can do

## The feature that would make it different

Imagine telling your phone:

> "PenGuru, I wish Nuxel had a way to automatically switch to silent mode when I arrive at work."

Instead of merely explaining how to do it, PenGuru could:

1. Inspect available Nuxel location, audio and scheduling APIs.
2. Propose a local automation with the permissions it needs.
3. Generate or configure the necessary service or extension.
4. Test it in isolation and show you exactly what will change.
5. Ask you to approve installation.
6. Activate the feature, monitor its operation and allow one-tap rollback.

Now imagine the same thing for custom Quick Settings toggles, automated backups, battery optimizations, application shortcuts or personalized workflows.

That's much more interesting than another chatbot app.

## Can your actual phones run it?

Yes, with some realistic constraints.

| Model class | Quantized weights (approx.) | Practical use                                       |
| ----------- | --------------------------- | --------------------------------------------------- |
| 0.5–1B      | 0.4–0.9 GB                  | Commands, classification, simple automation         |
| 1.5–2B      | 1–1.6 GB                    | Stronger instructions and tool calling              |
| 3–4B        | 2–3 GB                      | More capable local assistant and basic coding       |
| 7–8B        | 4–6 GB                      | Heavier reasoning; likely uncomfortable on the S10+ |

These are approximate Q4 model-weight sizes, not total runtime RAM. KV cache, context, system processes and runtime buffers add memory usage.

Your Galaxy S10+ with its Exynos 9820 is the challenging target. Most configurations have 8 GB RAM, with some 12 GB variants.

I'd start with a 1–2B quantized model, using `llama.cpp` on ARM64 CPU, with optional 3–4B models for devices with enough available RAM.

I would not assume Samsung's GPU or NPU can accelerate inference on Nuxel. Accessing those accelerators under native Fedora Linux may require substantial driver and runtime engineering.

And I'd enforce battery, temperature and memory limits. A local agent that drains the battery or stalls the graphical interface wouldn't feel intelligent.

## The architecture I'd build

PenGuru UI

Chat · Voice later · Automation dashboard

Local Model Runtime

llama.cpp · GGUF · Configurable small models

Capability & Permission Broker

Explicit scopes · Per-action approval · Audit logs

Nuxel Settings

Automations

Linux Tools

Feature Builder

Nuxel OS · Fedora ARM64 · systemd · Wayland

The critical design decision is that PenGuru never needs unrestricted root access to be useful.

Give it APIs for normal operations and a separate privileged broker for sensitive actions. Any generated code should be treated as untrusted until tested and approved.

## And your obsession with CONTROL? I'd make that the defining principle.

## PenGuru Control Center

Concept

Enable PenGuru

Installable and removable AI subsystem

Allow network access

Off by default — local inference

Local task automation

Run explicitly approved workflows

Feature development

Generate changes in an isolated environment

Apply approved changes automatically

Only within explicitly authorized scopes, with rollback

Interactive settings mockup; these controls do not change your phone.

Everything defaults to OFF. Ideally, Nuxel shouldn't even load the model or launch its service until the user enables PenGuru.

## How far can self-improvement realistically go?

There's a meaningful difference between an AI customizing its environment and an AI safely upgrading its own OS.

Very achievable: Create automations, scripts, custom UI layouts, shortcuts, settings integrations and simple extensions.

Achievable with safeguards: Build new applications, add services, test patches, create packages, update user-space functionality and roll changes back.

Much harder: Independently implement hardware drivers, modify boot-critical services or rewrite kernel components. A 1–3B model won't reliably engineer those changes without substantial external help and validation.

I'd also distinguish self-improvement of Nuxel's functionality from training or modifying the LLM's own weights. The former can be practical through code generation and tool use. The latter is resource-intensive and not something I'd make the phone do by default.

## How I'd roll it out

I'd develop PenGuru in four stages: first a completely optional offline chat/model runner; then system tools and private automation; next an extension builder with unit tests, sandboxing and rollback; and finally a supervised Nuxel repair/development assistant.

For version one, I'd prioritize five truly useful operations: inspect system health, change settings, manage files, schedule local actions, and diagnose service failures.

That would already be a compelling demonstration.

The bigger opportunity: Nuxel could become a Linux phone where the owner isn't stuck waiting for the OS developer to add every missing feature. The owner can describe what they want, and PenGuru helps create it—while the user retains control over what gets installed or executed.

That's a stronger differentiator than just bundling a small LLM.

And I particularly like the name PenGuru. It feels native to the Nuxel penguin identity without sounding like a generic commercial AI assistant.

I'd make its guiding rule:

“PenGuru may suggest anything, may prepare what it can verify, and may change only what its owner authorizes.”&#x20;