---
title: "DevFlow Kit: turning Jira tickets into pull requests with agents"
date: 2026-07-18
summary: "A multi-agent system that takes a rough Jira ticket and produces a reviewable pull request — running entirely on GitHub Actions, with no infrastructure to stand up."
tags: [ai-agents, langgraph, automation]
---

Most of the work between "here's a ticket" and "here's a pull request" is not the
interesting part of engineering. It's reading a vague ticket, asking the
questions that should have been in it, breaking the work into steps, wiring up a
branch, and keeping the tracker in sync. DevFlow Kit is my attempt to hand that
middle to a set of agents — and get back a PR a human can actually review.

## The shape of the problem

A ticket-to-PR cycle usually looks like this: someone refines the ticket, someone
picks it up, implements it, opens a PR, and updates Jira along the way. Each hand-off
is a place where context is lost and time leaks. The cycle routinely takes days,
most of it waiting rather than working.

The insight is that each of those steps is a *different kind* of task, so it wants
a different agent — not one giant prompt trying to do everything.

## Three agents, one pipeline

DevFlow Kit is organised as a small pipeline of specialised agents:

- **Refinement** — reads the raw ticket, resolves ambiguity, and rewrites it into a
  sprint-ready spec with clear acceptance criteria. A vague "add search to the
  dashboard" becomes something a machine (or a junior engineer) could act on
  without guessing.
- **Implementation** — takes the refined spec and produces the actual change,
  decomposing anything non-trivial into parallel subtasks rather than attempting one
  monolithic edit.
- **Jira-sync** — keeps the tracker honest: status, links, and PR state flow back so
  the board reflects reality without anyone updating it by hand.

Orchestration is handled with LangGraph, which makes the hand-offs between agents
explicit — each stage has defined inputs and outputs, so the flow is inspectable
rather than a black box.

## Zero added infrastructure

The design constraint I cared most about: **nothing new to run**. No server, no
queue, no hosted service to pay for and secure. The whole thing executes on GitHub
Actions, with the LLM calls made through the Claude Code CLI. You fork the repo,
connect it to Jira, and the agents run inside CI you already have.

It's also provider-agnostic — the model layer can sit on Anthropic, OpenAI, or
Google, so the pipeline isn't married to a single vendor's API or pricing.

## What it changes

Target repositories stay untouched — the agents open issues and pull requests
rather than pushing directly, so a human is always the last checkpoint before
anything merges. In practice that collapses the ticket-to-PR cycle from days to
hours, and moves the engineer's attention from shepherding tickets to reviewing
real diffs.

The code is open source — [DevFlow Kit on GitHub](https://github.com/manas-rai/devflow-kit),
with a [project site](https://manas-rai.github.io/devflow-kit-site/) walking through
the setup. It builds on two smaller pieces I wrote first:
[jira-refinement-agent](https://github.com/manas-rai/jira-refinement-agent) and
[spec-to-pr-orchestrator](https://github.com/manas-rai/spec-to-pr-orchestrator).
