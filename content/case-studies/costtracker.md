---
title: "CostTracker"
subtitle: "Open-source, self-hosted LLM cost tracking — a drop-in SDK that meters every OpenAI, Anthropic, Groq, and Bedrock call and writes usage and cost straight to your own database."
tech: [Python, ClickHouse, PostgreSQL]
github: https://github.com/manas-rai/costtracker
diagram: costtracker-architecture.svg
diagram_caption: "The SDK wraps each provider's client: calls pass through unchanged, tokens are metered from the response, priced against a synced pricing table, and written directly to ClickHouse or PostgreSQL with attribution tags. A bundled dashboard reads the same database. There is no ingestion server anywhere."
---

## The problem

The moment an LLM product gets real traffic, "what is this costing us?" becomes a
daily question — and the provider dashboards can't answer it the way a business
asks it. They show spend per API key; a product needs spend **per customer, per
feature, per model**. The SaaS tools that do this want you to proxy your LLM
traffic through their servers, which is a latency tax, a new point of failure,
and — for the same teams that care most, like the healthcare platforms I build —
a data-governance non-starter.

CostTracker is the self-hosted answer: keep the calls in your infrastructure,
keep the data in your database, and still get per-request cost analytics.

## The design: a drop-in wrapper, no middleman

The core decision is that **tracking rides inside the SDK** instead of behind a
proxy or ingestion server. You swap your provider client for CostTracker's
wrapper — `OpenAIClient`, `AnthropicClient`, `GroqClient`, `BedrockClient` —
and change nothing else. The wrapper forwards the call to the provider,
reads token usage off the response, prices it, and **writes the record
directly to your database**. Nothing new to deploy, no service between you and
your provider, and if the write ever had a problem it's your database, not a
third party, holding your usage data.

Each record carries **attribution tags** — `customer_id`, `feature` — set where
the client is constructed. That one small API choice is what turns raw usage
into the numbers people actually ask for: cost per customer, cost per feature,
margin per plan.

## Pricing 1,800+ models without maintaining a price list

Hand-maintaining LLM prices is a losing game — providers change them
constantly. CostTracker syncs its pricing table from **LiteLLM's public
pricing data** (`make sync-prices`), covering 1,800+ models across providers,
so cost computation stays current without anyone editing a price file.

## Two databases, one schema

Analytics on per-request events is a columnar workload, so production targets
**ClickHouse** — millions of usage rows aggregate in milliseconds. But
demanding ClickHouse just to try the tool would be hostile, so the same schema
runs on **PostgreSQL** for local development and small deployments. The
repository layer abstracts the difference; switching is configuration, not
code.

A bundled **analytics dashboard** (FastAPI server + UI) reads whichever
database you chose: spend over time, by model, by customer, by feature.

## What it demonstrates

CostTracker is the operations side of my GenAI work: the same concerns —
token metering, per-request cost attribution, observability of LLM spend — that
I wire into production platforms with LangSmith, built here as a standalone,
self-hosted open-source tool. Code is
[on GitHub](https://github.com/manas-rai/costtracker).
