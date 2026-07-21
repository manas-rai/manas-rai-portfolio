---
title: "Healthcare RAG Platform"
subtitle: "A multi-tenant Retrieval-Augmented Generation platform taken from zero to production — load-tested for 2,000+ concurrent sessions at sub-second latency."
tech: [Python, FastAPI, RAG, Azure OpenAI, Vector search, Multi-tenant]
diagram: healthcare-rag-architecture.svg
diagram_caption: "Each tenant's requests are authenticated and routed, then answered by a RAG service that retrieves only from that tenant's isolated vector store before generating a grounded response. Isolation runs the full depth of the stack."
---

*Professional work delivered for a healthcare product. This write-up describes
the architecture and engineering at a high level; it names no client and
includes no proprietary detail.*

## The problem

A healthcare product needed an assistant that could answer questions grounded in
each customer's own documents — not a general chatbot, and emphatically not one
where one customer's data could ever surface for another. Three constraints
shaped everything:

- **Strict tenant isolation.** In healthcare, "tenant A never sees tenant B's
  data" is not a nice-to-have; it's the whole product. Isolation had to hold at
  every layer, not just the UI.
- **Grounded, not generative-guessing.** Answers had to come from the tenant's
  actual documents, with citations — hallucination is a safety issue here.
- **Production scale from day one.** It had to hold up under real concurrent
  load, not just a demo.

## The approach

The system is a **multi-tenant RAG pipeline**. A request is authenticated and
tagged with its tenant identity first; from that point on, tenant is a
first-class part of every operation. The RAG service retrieves only from that
tenant's **isolated vector store**, assembles the grounded context, and calls
the LLM to generate an answer with citations back to the source documents.

The decision that mattered most was pushing **isolation down the whole stack**
rather than filtering at the top. Tenant-partitioned vector stores and data
partitioning mean a query physically cannot reach another tenant's data — there
is no code path where a missed `WHERE` clause leaks records, because the data
isn't in the same place to begin with.

## Production readiness

Getting a RAG demo working is easy; getting one that holds at scale is the job.
The platform was **load-tested for 2,000+ concurrent sessions at sub-second
latency**, which drove real engineering: connection and resource management
under concurrency, keeping retrieval fast as document volume grew, and making
sure the isolation guarantees held *under* load, not just in isolation.

## The outcome

The platform went from zero to production and directly enabled the product's
first paying customers. It's the work I point to when the question is "can you
own a GenAI system end to end — architecture, backend, cloud, and the
production launch — not just prototype a model call." This one, I did.
