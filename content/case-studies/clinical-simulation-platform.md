---
title: "Clinical Simulation Platform"
subtitle: "An LLM-powered platform that role-plays realistic patients for physician training — prompt-engineered personas grounded with RAG, load-tested for 2,000 concurrent sessions at sub-second latency."
tech: [Python, FastAPI, RAG, Prompt engineering, LLM]
diagram: clinical-sim-architecture.svg
diagram_caption: "Each turn, the simulation service assembles a prompt-engineered patient persona, context retrieved via RAG, and the conversation history, then calls the LLM to produce an in-character patient reply — a closed loop the physician converses with."
---

*Professional work delivered for a healthcare product. This write-up describes
the architecture and engineering at a high level; it names no client and
includes no proprietary detail.*

## The problem

Physicians train on patient interactions, but real standardized patients are
expensive, scarce, and hard to schedule at scale. The goal was a platform where
a physician-in-training could hold a realistic clinical conversation with a
simulated patient — one that stays *in character*, stays *medically consistent*,
and can be spun up on demand, for many trainees at once.

That combination is harder than it sounds. A generic chatbot breaks character,
contradicts its own history, or drifts into medically implausible territory —
all of which are training-destroying in this context.

## The approach

The platform is a **conversation loop** built on two techniques working together:

- **Prompt engineering** defines the patient **persona** — the condition,
  history, personality, and emotional state the LLM must inhabit and hold
  consistently across a multi-turn conversation. This is what keeps the
  simulated patient *in character*.
- **RAG** grounds each reply in **case and clinical knowledge**, so the patient's
  answers stay medically consistent with their presented condition rather than
  being invented on the fly. This is what keeps the simulation *plausible*.

For each turn, the **simulation service** assembles the persona, the retrieved
context, and the running **conversation history**, then calls the LLM to produce
an in-character reply. Maintaining that history is what lets the patient
"remember" what they said three turns ago — the difference between a believable
encounter and a goldfish.

## Production readiness

Like the RAG platform it sits alongside, this was built to hold under real load:
**load-tested for 2,000 concurrent sessions at sub-second response latency**.
Conversational simulation is unforgiving of lag — a training encounter that
stalls between turns breaks immersion — so keeping per-turn latency low under
concurrency was a first-class engineering goal, not a nice-to-have.

## The outcome

The platform gives trainees realistic, on-demand patient encounters without the
logistics of standardized patients — and it's a second production GenAI system I
took from prompt design through load-tested launch, alongside the multi-tenant
[Healthcare RAG Platform](/projects/healthcare-rag-platform/).
