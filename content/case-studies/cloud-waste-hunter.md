---
title: "Cloud Waste Hunter"
subtitle: "ML-powered AWS waste detection with a safety-first remediation pipeline — find idle resources automatically, delete them only with a dry-run, an approval, an audit log, and a 7-day rollback."
tech: [Python, FastAPI, scikit-learn, Next.js]
github: https://github.com/manas-rai/cloud-waste-hunter
diagram: cloud-waste-hunter-architecture.svg
diagram_caption: "Detect: boto3 scanners read inventory and CloudWatch metrics; an Isolation Forest flags idle EC2, rules flag unattached EBS volumes and old snapshots; findings land in PostgreSQL. Act: review in the dashboard, dry-run, human approval, audit-logged execution — with a 7-day rollback window on everything."
---

## The problem

Every AWS account accumulates waste: instances someone spun up for a test and
forgot, EBS volumes orphaned when their instance died, snapshots nobody will
ever restore. It's pure burn — but the reason it survives is that *deleting
things in production is scary*. The cost of a wrong deletion dwarfs months of
savings, so the safe move is always "leave it," and the waste compounds.

Cloud Waste Hunter's premise: the detection should be automated, and the
deletion should be so guarded that acting on a finding is no longer scary.

## Detection: ML where it helps, rules where they're enough

Scanners read resource inventory and **CloudWatch metrics** via boto3, and a
detection layer classifies waste — deliberately using different tools for
different problems:

- **Idle EC2 instances** get an ML treatment: an **Isolation Forest**
  (scikit-learn) over utilization patterns, targeting instances sitting under
  ~5% CPU for a week or more. Anomaly detection fits here because "idle" isn't
  one clean threshold — usage patterns vary, and outlier detection catches the
  shape of abandonment better than a single cutoff.
- **Unattached EBS volumes** (30+ days) and **old snapshots** (90+ days with no
  associated AMI) use plain rules — because for these, a rule *is* the right
  model, and pretending otherwise would be ML theater.

Findings land in **PostgreSQL** and surface in a **Next.js dashboard** with the
estimated monthly saving per resource.

## Remediation: the safety pipeline is the product

The detection is useful; the safety design is what makes anyone actually press
the button. Nothing is ever deleted directly from a finding:

1. **Dry-run** — every action can be previewed: exactly what would be deleted,
   and what it depends on.
2. **Manual approval** — a human confirms each execution; there is no
   fully-automatic destroy path.
3. **Audit log** — every action is recorded: who approved what, when, and what
   happened.
4. **7-day rollback** — executed actions remain reversible for a week
   (snapshot-before-delete style), so even an approved mistake is recoverable.

That ordering — preview, approve, log, undo-window — is the same
human-in-the-loop philosophy as my agent systems: automate the analysis
completely, gate the irreversible step on a person.

## The stack

**FastAPI** backend in a layered architecture (API → services → repositories →
detection / aws / safety), **scikit-learn** for the ML, **boto3** against AWS,
**PostgreSQL** for state, **Next.js/TypeScript** dashboard, and **Terraform**
for the infrastructure. Open source —
[on GitHub](https://github.com/manas-rai/cloud-waste-hunter).
