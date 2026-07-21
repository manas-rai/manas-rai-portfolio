---
title: "Healthcare RAG Platform"
subtitle: "A multi-tenant Retrieval-Augmented Generation platform on Azure, taken from zero to production — load-tested for 2,000+ concurrent sessions at sub-second latency."
tech: [Python, FastAPI, Azure AI Search, Azure OpenAI, Azure AD B2C, Document Intelligence, LangChain, Cosmos DB, RAGAS, Multi-tenant]
diagram: healthcare-rag-architecture.svg
diagram_caption: "Ingestion (top) is triggered via Service Bus and Azure Functions when documents land in tenant-isolated Blob Storage. Query (bottom) authenticates with Azure AD B2C, rewrites the query, runs hybrid search with a semantic reranker and tenant filter, and generates a grounded answer with GPT-4o. Content safety, caching, per-tenant history, evaluation, and cost tracking wrap the whole thing."
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
container — the upload publishes a message to **Azure Service Bus**, which fires
an **Azure Functions** worker. Decoupling the trigger through a queue means
ingestion absorbs bursts without dropping work. The worker then:

1. Parses each document with **Azure AI Document Intelligence**, handling the
   messy real-world formats (PDFs, scans, tables) that naive text extraction
   chokes on.
2. Splits the text with a **LangChain semantic chunker** — on meaning rather
   than fixed character counts, so a chunk is a coherent idea instead of an
   arbitrary window, which materially improves retrieval quality.
3. Embeds the chunks with **text-embedding-3-large** and writes them to a
   **per-tenant Azure AI Search index**.

Because it's trigger-driven, a customer's new document is searchable shortly
after upload, with no manual re-indexing step.

## Query: authenticated, hybrid, tenant-scoped retrieval

On the serving side, the **RAG service** is a **FastAPI** app on **Azure App
Service**. A request is authenticated first by **Azure AD B2C**, which
establishes tenant identity and claims. From there, tenant is a first-class part
of every operation:

- The query is **rewritten and expanded** before retrieval, so a terse user
  question becomes a fuller search that surfaces the right passages.
- Retrieval is a **hybrid search** over Azure AI Search — keyword *and* vector,
  which beats either alone for the domain terms and exact codes common in
  healthcare — followed by the **semantic reranker** to push the most relevant
  passages to the top.
- A **tenant filter** is applied on every query, so retrieval is physically
  scoped to that tenant's data. Combined with per-tenant blob containers and B2C
  claims, isolation runs the full depth of the stack — there is no code path
  where a missed filter leaks another tenant's records.
- The reranked context goes to **Azure OpenAI (GPT-4o)**, which generates the
  answer with citations back to the source documents.

## Safety, performance, and operations

The concerns that turn a working demo into a product a healthcare company will
actually run:

- **Azure AI Content Safety** screens inputs and outputs — a real requirement in
  a clinical context, not an afterthought.
- **Azure Cache for Redis** absorbs repeated and hot queries, cutting latency and
  cost. **Per-tenant rate limiting** keeps one noisy tenant from degrading the
  others.
- **Cosmos DB**, a collection per tenant, holds conversation history — isolation
  extends to memory, not just retrieval.
- **RAGAS** drives evaluation of answer groundedness and relevance, and a **user
  feedback loop** (thumbs) feeds back into tuning. **LangSmith** tracks token
  usage and cost per call, so quality and spend are both observable.

## Production readiness

Getting a RAG demo working is easy; getting one that holds at scale is the job.
The platform was **load-tested for 2,000+ concurrent sessions at sub-second
latency**, which drove real engineering: connection and resource management
under concurrency, keeping hybrid retrieval and reranking fast as document
volume grew, and verifying the isolation guarantees held *under* load.

## The outcome

The platform went from zero to production and directly enabled the product's
first paying customers. It's the work I point to when the question is "can you
own a GenAI system end to end — architecture, ingestion, retrieval, safety,
cloud, and the production launch — not just prototype a model call." This one,
I did.
