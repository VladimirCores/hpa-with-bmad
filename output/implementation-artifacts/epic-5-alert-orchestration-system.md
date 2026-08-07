# Epic 5: Alert Orchestration System

## Goal

Build a directed, replay-capable alert system using Kafka, Pulsar, and state machines.

## Stories

| ID | Priority | Description |
|---|---|---|
| 5-1 | HIGH | Ingest alert signals through directed Kafka streams |
| 5-2 | HIGH | Persist alert state machine transitions |
| 5-3 | HIGH | Trigger automated alert responses |
| 5-4 | HIGH | Manage human alert handling with audit trail |
| 5-5 | MEDIUM | Provide basic LLM decision support for alerts |

## Architecture Notes

- Use Kafka for ingestion, Pulsar for streaming/state persistence
- Leverage Pulsar Functions for stateful processing
- Cross-signer architecture: alerts → Kafka → Pulsar → Actions