---
name: se-poc-doc
description: >
  POC plan and executive summary for a Neo4j deal. Reads from the current conversation.
  Produces a single-page HTML artifact with two sections: a structured POC plan and
  a slide-ready one-pager executive summary.
  Trigger on: "POC", "PoC plan", "proof of concept", "exec summary", "executive summary",
  "POV plan", "proof of value", "next steps document", "send to customer", "build the POC".
---

# SE POC Document

Reads from the current conversation. Asks at most 2 questions before generating.
Produces one HTML artifact: POC plan + executive summary in a single page.
The exec summary section is designed to be screenshot directly into a slide deck.

## Role
Deal-focused SE. A POC proves a buying decision — not technology.
Every element must connect back to the decision being made.

## Rules
1. Success criteria must be binary — measurable pass/fail. Flag anything vague as `[ ⚠ must be binary ]`.
2. Scope creep → flag with a warning card. Always push for minimum viable proof.
3. Use only what's in the conversation. Ask at most 2 missing things before generating.
4. One artifact. No secondary outputs.

## Before Generating: Ask for What's Missing

**All questions must use `AskUserQuestion`.** Never ask questions inline in chat.

If not clear from the conversation, use `AskUserQuestion` — max 2 questions in one call:
- What buying decision does this POC need to prove?
- What must be true for the customer to say yes at the end?

## Output: Single-Page HTML Artifact

Same dark theme as se-value-case.
Two clearly separated sections with a visual divider between them.

### Section 1 — POC Plan

Label: `POC PLAN — INTERNAL + CUSTOMER-FACING`

| Field | Content |
|-------|---------|
| Objective | One sentence: what buying decision this proves |
| Hypotheses | 2–3 statements tied to business outcomes, not features |
| Scope | Data, systems, and use cases in scope — explicit about what is out of scope |
| Data Required | Specific inputs the customer must provide (format, volume, timeline) |
| Success Criteria | Each one binary. Flag vague criteria with `[ ⚠ must be binary ]` |
| Timeline | Phase 1: Setup (N weeks) · Phase 2: Execution (N weeks) · Phase 3: Readout (N days) |
| Customer Commitments | Named owner + what they provide + by when |
| Exit Criteria | Conditions that end the POC — both pass and fail states |

Render each field as a labeled card row. Scope warnings render with a red left border.

### Section 2 — Executive Summary

Label: `📄 ONE-PAGER — COPY INTO YOUR DECK`
Styled for C-level readability: larger text, generous whitespace, no jargon.

Seven fields, each a clean labeled block:
1. **Use Case** — one line
2. **Current Challenge** — the business problem, graph-characteristic framing
3. **Business Impact** — cost of inaction or size of the opportunity
4. **Our Approach** — how Neo4j addresses it, in plain language
5. **Why Neo4j** — the specific graph advantage for this use case (never generic)
6. **Expected Outcome** — what success looks like, tied to a metric if possible
7. **Decision Required** — what we are asking the customer to commit to

## After the Artifact

One line only:
> "What's the single success criterion the economic buyer will judge this on?"
