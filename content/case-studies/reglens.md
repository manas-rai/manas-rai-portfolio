---
title: "RegLens"
subtitle: "Multi-agent regulatory compliance automation — feed it a regulation and your control matrix, and specialised agents extract every obligation, find the gaps against your policies, score them by risk, and draft an audit report a human signs off."
tech: [Python, LangGraph, Google ADK, A2A / JSON-RPC, Gemini, Claude, pgvector, FastAPI, RAGAS, Next.js]
github: https://github.com/manas-rai/reglens
demo: https://manas-rai.github.io/reglens/
diagram: reglens-architecture.svg
diagram_caption: "A LangGraph supervisor, checkpointed in Postgres, runs the pipeline: ingest → retrieve policies → gap analysis → score risks → report → human sign-off. It delegates to A2A agents over JSON-RPC (Gemini for multimodal ingestion and risk scoring) and runs structured gap analysis with Claude over a pgvector policy store."
---

## The problem

Regulatory compliance review is slow, manual, and unforgiving. A new circular
lands, and someone has to read it end to end, pull out every obligation, check
each one against the organisation's existing policies, judge how bad each gap is,
and write it up. It's exactly the kind of work that's too high-stakes to fully
automate — a wrong "you're compliant" is worse than no answer — but too tedious
to do well by hand at volume.

RegLens automates the *legwork* while keeping a human on the *judgment*: it does
the extraction, retrieval, gap-finding, and drafting, then stops and asks a
compliance reviewer to approve, edit, or reject before anything is final.

## The architecture: a supervisor and specialist agents

The system is deliberately **multi-agent**, not one monolithic prompt. A
**LangGraph supervisor** owns the pipeline — *ingest → retrieve policies → gap
analysis → score risks → generate report → human-in-the-loop gate* — and
delegates each specialised step to a dedicated worker:

- **Ingestion agent** — turns a regulatory PDF into a structured list of
  obligations using **Gemini's multimodal** capability, so it reads tables and
  scanned layouts, not just clean text.
- **Policy retrieval** — a **pgvector** RAG store holds the organisation's
  control matrix; each obligation retrieves the policies most likely to cover it.
- **Gap analysis** — **Claude** compares each obligation against the retrieved
  policies and returns a *structured* verdict (covered / partial / missing) — no
  free-text parsing, the model emits typed output.
- **Risk scorer** — a second agent scores each gap against a domain risk rubric,
  again on **Gemini**.

The two agents run as **separate services** and are called over the
**Agent-to-Agent (A2A) protocol via JSON-RPC 2.0** — each publishes a
`/.well-known/agent-card.json` describing its skills, so the supervisor
discovers and invokes capabilities rather than hard-wiring HTTP calls. Pydantic
schemas are the contract between every service.

## Why multiple models

RegLens uses **Gemini and Claude on purpose**, not by accident: Gemini's
multimodal reading handles messy regulatory PDFs, while Claude's structured
output is the reliable choice for the gap-analysis reasoning that has to come
back as clean, typed data. Matching the model to the sub-task beats forcing one
model to do everything.

## Durable, resumable, and human-gated

The supervisor is **checkpointed in Postgres** (LangGraph's Postgres
checkpointer), so a run is durable and resumable — and crucially, the pipeline
*interrupts* at the report stage. The reviewer sees the draft, and can approve
as-is, override individual gap verdicts inline, or reject the run. Progress
streams to the client the whole way through over **SSE**, so a long run is
observable rather than a black box. Everything — run state, checkpoints, policy
embeddings, and an audit log — lives in one Postgres instance.

## Trusting an agent system: the evals harness

The part I'm proudest of is how RegLens is *tested*, because "the agents seem to
work" isn't good enough for compliance. The evals harness goes well beyond a
happy-path check:

- **Component evals** with labelled golden datasets for each stage — ingestion,
  retrieval, gap analysis, risk scoring, and routing.
- **Behavioral tests** — *monotonicity* (more severe inputs never score lower
  risk), *invariance* (irrelevant rewording doesn't change the verdict), and
  *counterfactual* checks — the kind of properties that catch silent regressions
  a single accuracy number hides.
- **Guards** for the RAG, the A2A calls, and the LLM outputs, plus **Presidio**
  for PII detection.
- Scored with **RAGAS** and **DeepEval**, and traced end to end with
  **LangSmith**, on top of **OpenTelemetry** and structured logging.

That harness is what the résumé calls the "drift-detection evaluation harness" —
it's how you keep a multi-agent system honest as models and prompts change.

## The stack

Python · **FastAPI** (REST + SSE) · **LangGraph** supervisor · **Google ADK**
agents over **A2A / JSON-RPC 2.0** · **Gemini** (multimodal + embeddings) ·
**Claude** (structured gap analysis) · **pgvector** on **PostgreSQL** ·
**RAGAS / DeepEval / Presidio** evals · **OpenTelemetry** + **LangSmith** ·
**Next.js** UI · **Docker Compose** + **Terraform**. Open source —
[on GitHub](https://github.com/manas-rai/reglens).
