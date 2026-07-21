---
title: "Clinical Simulation Platform"
subtitle: "An LLM-powered platform that role-plays realistic patients for physician training — real-time text and voice, plus an automated feedback report that scores the trainee. Load-tested for 2,000 concurrent sessions at sub-second latency."
tech: [Python, Go, AWS, EKS, OpenAI, Anthropic, Realtime voice, WebSockets, PostgreSQL, LIT]
diagram: clinical-sim-architecture.svg
diagram_caption: "Two halves. Authoring (top): illness scripts become case content via an authoring service, validated by a human, stored in a CMS, and delivered over a CDN. Runtime (bottom): a physician converses — text or voice — with a simulation service that fetches the versioned system prompt from LangSmith, injects the case JSON, and calls a config-driven, multi-provider LLM; at the end, a feedback report scores their questions and investigations."
---

*Professional work delivered for a healthcare product. This write-up describes
the architecture and engineering at a high level; it names no client and
includes no proprietary detail. The patient cases are **authored** — there is no
real patient data.*

## The problem

Medical students and physicians train on patient encounters, but real
standardized patients are expensive, scarce, and hard to schedule at scale. The
goal was a platform where a trainee could hold a realistic clinical conversation
with a simulated patient — one that stays *in character*, is *medically
consistent*, works over **text or voice**, and can be spun up on demand for many
trainees at once. And critically, it had to *assess* the trainee afterward, not
just chat.

## Authoring: turning illness scripts into cases

The content is built, not retrieved. An **authoring service** turns clinical
*illness scripts* into structured case content, which a **human reviewer
validates** before it's committed to a **CMS**. From there cases are published
to **S3** and served through **CloudFront**, so the runtime pulls case content
from a CDN edge rather than a live database. Human-in-the-loop validation is
non-negotiable here — a medically wrong case teaches the wrong thing.

## Runtime: the simulation loop

The front end is built in **LIT** and talks to the backend over **WebSockets**,
supporting both **text and voice**. The **simulation service** runs on **AWS
EKS**, written in **Python and Go**, with **Cognito** handling authentication.

The design decision worth calling out: **there is no RAG.** For each turn the
service assembles the prompt from two sources — the **system prompt** (the
prompt-engineered persona and guardrails) is fetched and version-managed from
**LangSmith**, and the specific **case JSON** (condition, history, the patient's
story) is pulled from the **CDN** and injected wholesale. The whole case fits in
context, so retrieval would add latency and non-determinism for no benefit —
injecting it directly is simpler, fully reproducible, and easier to validate.
The prompt guardrails keep the patient from breaking role.

Model selection is **config-driven and provider-agnostic**: text conversations
can run on **OpenAI** (GPT-4o / 5.4 / 5.6-sol) or **Anthropic** (Claude Sonnet 5
/ Haiku 4.5 / Opus 4.7), and voice runs on **GPT Realtime** — switching model or
provider is a config change, not a code change. That keeps the platform off any
single vendor's roadmap and pricing. **LangChain** abstracts across providers,
and each interaction is persisted per session in **PostgreSQL**.

## Assessment: the feedback report

The feature that makes it a *training* tool, not just a chatbot: during an
encounter the trainee **selects the questions to ask and the investigations to
order**, and at the end the platform generates a **feedback report** evaluating
those choices — a complete picture of how they approached the case. Simulation
and evaluation quality are checked against a **gold dataset**.

## Production readiness

Built to hold under real load — **2,000 concurrent sessions at sub-second
latency**. Conversational simulation, especially voice, is unforgiving of lag,
so that came from **async I/O, connection pooling, and an in-memory cache**, with
**per-session and per-user rate limiting** to protect capacity. It's covered by
**k6** for load and integration testing and **Playwright** for end-to-end, and
observed with **Datadog** (logs), **New Relic** (monitoring), and **LangSmith**
(LLM traces and cost).

## The outcome

The platform gives trainees realistic, on-demand patient encounters — in text
and voice — plus an automated assessment of their clinical reasoning, without the
logistics of standardized patients. It's a second production GenAI system I took
from design through load-tested launch, alongside the multi-tenant
[Healthcare RAG Platform](/projects/healthcare-rag-platform/) — and a deliberately
*different* architecture, because this problem didn't need retrieval.
