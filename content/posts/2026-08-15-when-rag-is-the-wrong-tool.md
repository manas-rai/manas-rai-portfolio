---
title: "When RAG is the wrong tool"
date: 2026-08-15
summary: "I built a multi-tenant RAG platform and a simulation platform with no retrieval in it at all. The test that separates them is simpler than it looks."
tags: [ai-agents, rag, architecture]
---

Most LLM product proposals I see open the same way: a vector database, an
embedding model, and a retrieval step. RAG has become the default shape of an AI
feature, to the point where "how will we do retrieval" gets asked before "what
context does the model actually need".

I've shipped both answers. One platform is RAG the whole way down — hybrid
search, a semantic reranker, per-tenant indexes. The other is a conversational
simulation platform with **no retrieval in it at all**, and that was a deliberate
call rather than a shortcut.

The test that separates them turns out to be one question.

## The question

**Do you know, before the request arrives, exactly what context the model needs?**

If you don't, you have a search problem, and retrieval is the right tool. If you
do, retrieval is a slower and less reliable way to do something you could have
done directly.

That's it. Everything below is what the two answers look like in practice.

## Where the answer is no

The healthcare platform is a multi-tenant assistant answering questions grounded
in each customer's own documents. A user can ask anything about a corpus that
only they can see, and which changes whenever they upload something new.

There's no way to know which passages matter until the question exists. So the
whole system is built around finding them: documents are chunked semantically
rather than on character counts, embedded into a per-tenant search index, and
retrieved with hybrid search — keyword *and* vector, because healthcare is full
of exact codes and domain terms where neither alone is enough — then reordered by
a semantic reranker before anything reaches the model.

That is what retrieval is for. Unknown question, large corpus, relevance you can
only compute at request time.

## Where the answer is yes

The clinical simulation platform lets a trainee hold a realistic conversation
with a simulated patient, over text or voice, and then scores how they
approached the case.

Every single turn needs exactly two things: the persona and guardrails that keep
the patient in character, and the specific case being simulated — the condition,
the history, the patient's story. Both are known before the conversation starts.
Neither is a search problem.

So the service assembles the prompt directly. The system prompt is fetched and
version-managed from LangSmith. The case JSON comes from a CDN and is injected
wholesale. The whole case fits in context, so there is nothing to retrieve.

The content side reinforces it: cases are **built, not retrieved**. An authoring
service turns clinical illness scripts into structured cases, a human reviewer
validates each one before it's committed, and they're published to S3 and served
through CloudFront. A medically wrong case teaches the wrong thing, so the review
gate matters more than any clever indexing would.

## What retrieval would have cost

Adding a retrieval step to that design would have bought nothing and charged for
it four times.

**Latency.** Voice conversation is unforgiving of lag. A retrieval round trip on
every turn is spent from a budget that was already tight.

**Determinism.** Injecting the case means the model sees exactly the case. A
retriever means it sees whatever the retriever returned, which is a different
thing on a bad day.

**Reproducibility.** This is an assessment tool. The same case has to behave the
same way for every trainee, or the feedback report isn't comparing like with
like. Retrieval quietly makes each run a little different.

**Validation.** You can put a case JSON in front of a clinician and ask "is this
right?" You cannot put "whatever the retriever surfaces at runtime" in front of
them and get a useful answer.

None of those is a retrieval bug. They're all just properties of adding a search
step where there was no search to do.

## The rule I use now

Retrieval is for when you don't know what you need. When you do know, inject it.

The failure mode I'd watch for isn't picking the wrong tool once — it's never
asking the question. If nobody on the team can say what context a request needs
before it arrives, that's worth finding out before choosing an architecture,
because the answer decides it for you.
