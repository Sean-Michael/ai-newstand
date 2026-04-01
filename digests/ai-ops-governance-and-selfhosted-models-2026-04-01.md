---
title: "AI Ops, Governance, and Self‑hosted Models | 2026-04-01"
date: 2026-04-01
---
# AI Ops, Governance, and Self‑hosted Models | 2026-04-01

## 🔥 Story of the Day
### [Run and Iterate on LLMs Faster with Docker Model Runner on DGX Station](https://www.docker.com/blog/blog-docker-model-runner-new-nvidia-dgx-station/) — Docker Blog  
NVIDIA’s DGX Station, a deskside platform powered by the GB300 Grace‑Blackwell Ultra Superchip, replaces the single‑GPU DGX Spark with a 72‑core Grace CPU and a Blackwell Ultra GPU linked via NVLink‑C2C. This architecture delivers data‑center‑class throughput while staying compact enough for a workstation.

Docker Model Runner now recognizes the new resource topology. By extending Docker’s device‑plugin interface to expose NVLink‑C2C bandwidth and GPU‑CPU memory pointers, the runner can schedule mixed‑compute jobs across the 72‑core CPU and Blackwell GPU without custom scripts. It also supports unified memory up to 128 GB, allowing full‑in‑memory inference of 10‑B parameter models locally.

For MLOps teams, this means a single Docker workflow can manage GPU‑accelerated training, CPU‑bound preprocessing, and inference on the same box. The tight integration removes the need to spin up remote GPU clusters during experimentation, reducing cloud bill spikes and latency for iterative model tuning.

The key technical detail is the injection of fine‑grained GPU bandwidth metrics into the Docker scheduler via the updated device‑plugin. This enables the container runtime to make informed placement decisions, ensuring that inference workloads get the necessary NVLink throughput while CPU‑bound tasks stay on the high‑core Grace CPU.

## ⚡ Quick Hits
### [Docker Sandboxes: Run Agents in YOLO Mode, Safely](https://www.docker.com/blog/docker-sandboxes-run-agents-in-yolo-mode-safely/) — Docker Blog  
Docker Sandboxes create a hard boundary around autonomous agents, preventing file‑system leaks or destructive commands. Running natively on a local machine, the sandbox supports agents such as Claude Code, GitHub Copilot CLI, Gemini CLI, and upcoming NanoClaw and OpenClaw. Teams report a 60 % lift in pull‑request merge rates when agents operate in sandboxed mode.

### [JetBrains: AI agents are about to repeat the cloud ROI crisis](https://thenewstack.io/jetbrains-central-ai-agents/) — The New Stack  
JetBrains Central is a governance‑and‑execution platform that tracks AI coding agent activity, performance, and cost. The tool mirrors early‑cloud cost‑management solutions, providing teams with observability and ROI proofing. Surveys indicate that while 90 % of developers use AI, only 13 % employ it across the full software‑development lifecycle, underscoring the need for centralized governance.

### [Portkey open-sources its AI gateway after processing 2 trillion tokens a day](https://thenewstack.io/portkey-gateway-open-source/) — The New Stack  
Portkey’s unified Portkey Gateway, now open‑source, functions as an AI‑tuned API gateway. It consolidates governance, observability, authentication, cost controls, and token‑cost tracking into a single control plane. Teams can deploy the gateway on Kubernetes, integrate it into existing CI/CD pipelines, and enforce agent‑behavior policies without relying on multiple SaaS vendors.

### [Inside Claude Code’s leaked source: swarms, daemons, and 44 features Anthropic kept behind flags](https://thenewstack.io/claude-code-source-leak/) — The New Stack  
Anthropic’s Claude Code v2.1.88 accidentally shipped a 59.8 MB source‑map exposing 512,000 lines of TypeScript across 1,900 files. The leak, forked 41,500 times on GitHub, revealed internal subsystems like a spinner‑verb subsystem with 187 whimsical actions. The incident highlights the need for automated packaging scans, source‑map stripping, and public mirror monitoring.

### [How to solve the AI paradox in software development with intelligent orchestration](https://thenewstack.io/solve-ai-paradox-orchestration/) — The New Stack  
The AI paradox shows that code‑generation tools alone yield limited productivity because coding represents only 52 minutes of the delivery pipeline. Fragmentation across isolated agents and uneven trust levels hinder scaling. The article advocates a unified AI stack that shares a common data model, context, and trust policy across the SDLC, emphasizing integration layers, shared embeddings, and transparent audit mechanisms.

### [Sustaining OpenTelemetry: Moving from dependency management to stewardship](https://www.cncf.io/blog/2026/03/31/sustaining-opentelemetry-moving-from-dependency-management-to-stewardship/) — CNCF Blog  
Bloomberg’s structured contributor‑pipeline model pairs new engineers with mentors to handle high‑leverage maintenance tasks in OpenTelemetry. Initially tested with pandas and NVIDIA, the program now extends to OpenTelemetry under CNCF. It aims to keep core libraries healthy and secure, reducing emergency patches and maintaining reliable AI deployments on Kubernetes.

---
*Researcher: gpt-oss:20b • Writer: gpt-oss:20b • Editor: gpt-oss:20b*
