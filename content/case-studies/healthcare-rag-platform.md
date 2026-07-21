---
title: "Healthcare RAG Platform"
subtitle: "A multi-tenant Retrieval-Augmented Generation platform on Azure, taken from zero to production — load-tested for 2,000+ concurrent sessions at sub-second latency."
tech: [Python, FastAPI, Azure, Azure AI Search, Azure OpenAI, Azure AD B2C, Document Intelligence, LangChain, Multi-tenant]
diagram: healthcare-rag-architecture.svg
diagram_caption: "Two pipelines share one per-tenant Azure AI Search index. Ingestion (top) is auto-triggered when documents land in tenant-isolated Blob Storage. Query (bottom) authenticates with Azure AD B2C, runs a hybrid search with a tenant filter, and generates a grounded answer. Isolation holds at every layer."
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

## Ingestion: documents to a searchable index

Everything is built on **Azure**. When a customer's documents land in
**Blob Storage** — partitioned so each tenant's files sit in their own isolated
container — an upload **automatically triggers** the indexing pipeline:

1. **Azure AI Document Intelligence** parses each document, handling the messy
   real-world formats (PDFs, scans, tables) that naive text extraction chokes on.
2. A **LangChain semantic chunker** splits the parsed text on meaning rather than
   fixed character counts, so a chunk is a coherent idea instead of an arbitrary
   window — which materially improves retrieval quality.
3. The chunks are embedded and written to a **per-tenant Azure AI Search index**.

Because it's trigger-driven, a customer's new document is searchable shortly
after upload, with no manual re-indexing step.

## Query: authenticated, hybrid, tenant-scoped retrieval

On the serving side, a request is authenticated first by **Azure AD B2C**, which
establishes tenant identity and claims. From there, tenant is a first-class part
of every operation:

- The **RAG service** (Python / FastAPI) runs a **hybrid search** over Azure AI
  Search — combining keyword and vector retrieval, which beats either alone,
  especially for the domain terms and exact codes common in healthcare.
- A **tenant filter** is applied on every query, so retrieval is physically
  scoped to that tenant's data. Combined with the per-tenant blob containers and
  B2C claims, isolation runs the full depth of the stack — there is no code path
  where a missed filter leaks another tenant's records.
- The retrieved context is passed to **Azure OpenAI**, which generates the answer
  with citations back to the source documents.

## Production readiness

Getting a RAG demo working is easy; getting one that holds at scale is the job.
The platform was **load-tested for 2,000+ concurrent sessions at sub-second
latency**, which drove real engineering: connection and resource management
under concurrency, keeping hybrid retrieval fast as document volume grew, and
verifying the isolation guarantees held *under* load, not just in isolation.

## The outcome

The platform went from zero to production and directly enabled the product's
first paying customers. It's the work I point to when the question is "can you
own a GenAI system end to end — architecture, ingestion, retrieval, cloud, and
the production launch — not just prototype a model call." This one, I did.
