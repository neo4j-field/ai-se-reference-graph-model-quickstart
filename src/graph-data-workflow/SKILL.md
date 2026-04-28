---
name: graph-data-workflow
description: >
  Generate realistic synthetic data for a Neo4j property graph by asking the user
  the right questions, then writing a Faker script tailored to their answers.
  Trigger when the user wants to populate Neo4j, generate fake/synthetic/test
  data for a graph schema, or build a dataset to test detection logic (fraud
  rings, entity resolution, anomalies). Trigger when the user uploads an
  arrows.app schema or describes a graph model and asks for sample data.
  Do NOT trigger for schema design (use graph-schema-studio).
---

# Graph Data Workflow

A six-step conversational flow: scale → use case → cardinality → preview →
patterns → script. Claude asks; the user answers; a Faker script is written
and run.

**Read `assets/docs/WORKFLOW.md` before starting.** It has the question
templates, the order, and the rules about pausing for confirmation.

Helper: `scripts/build_script.py` — takes a JSON config and emits a
standalone Python script using Faker.
