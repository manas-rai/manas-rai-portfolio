---
title: "DevFlow Kit"
subtitle: "Multi-agent SDLC automation — Jira ticket to reviewable pull request, with no infrastructure to run."
tech: [Python, LangGraph, GitHub Actions, Claude Code, Jira]
github: https://github.com/manas-rai/devflow-kit
demo: https://manas-rai.github.io/devflow-kit-site/
diagram: devflow-kit-architecture.svg
diagram_caption: "The pipeline: a Jira ticket flows through refinement and implementation agents to a pull request, while a Jira-sync agent keeps the board current. LangGraph orchestrates; GitHub Actions runs it."
---

## The problem

Most of the distance between "here's a ticket" and "here's a pull request" is
toil, not engineering. Someone reads a vague ticket and asks the questions that
should have been in it. Someone breaks the work into steps, wires up a branch,
and keeps the tracker in sync. Each hand-off loses context, and the cycle
routinely takes **days — most of it waiting, not working**.

The goal of DevFlow Kit is to hand that middle stretch to a set of agents and
get back a pull request a human can actually review.

## The approach

The key decision was **not** to throw one large prompt at the whole problem.
Each step between ticket and PR is a different kind of task, so each gets a
dedicated agent with a narrow job:

- **Refinement** reads the raw ticket, resolves ambiguity, and rewrites it into
  a sprint-ready spec with clear acceptance criteria.
- **Implementation** takes that spec and produces the change, decomposing
  anything non-trivial into parallel subtasks rather than one monolithic edit.
- **Jira-sync** keeps the tracker honest — status, links, and PR state flow back
  so the board reflects reality without anyone updating it by hand.

Orchestration runs on **LangGraph**, which makes the hand-offs explicit: every
stage has defined inputs and outputs, so the flow is inspectable instead of a
black box.

## The constraint that shaped it: zero infrastructure

The requirement I cared about most was that there be **nothing new to run** — no
server, no queue, no hosted service to pay for and secure. The whole pipeline
executes on **GitHub Actions**, with model calls made through the Claude Code
CLI. You fork the repo, connect it to Jira, and the agents run inside CI you
already have.

The model layer is **provider-agnostic** — Anthropic, OpenAI, or Google — so the
system isn't married to one vendor's API or pricing.

## What it changes

Target repositories stay untouched: the agents open issues and pull requests
rather than pushing directly, so a human is always the last checkpoint before
anything merges. In practice that collapses the ticket-to-PR cycle **from days
to hours**, and shifts the engineer's attention from shepherding tickets to
reviewing real diffs.

It builds on two smaller pieces I wrote first —
[jira-refinement-agent](https://github.com/manas-rai/jira-refinement-agent) and
[spec-to-pr-orchestrator](https://github.com/manas-rai/spec-to-pr-orchestrator) —
now composed into one pipeline.
