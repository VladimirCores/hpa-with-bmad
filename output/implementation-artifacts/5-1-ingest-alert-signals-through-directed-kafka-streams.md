# Story 5-1: Ingest Alert Signals Through Directed Kafka Streams

Status: done

Baseline commit: c97407f

## Story

As a Platform Engineer,
I want alert signals ingested through directed Kafka streams,
so that alerts are queued reliably for Pulsar-based processing.

## Acceptance Criteria

1. Given an alert signal arrives, when the Kafka topic exists, then the signal is persisted to topic within 100ms.
2. Given peak load of 10k alerts/sec, when alerts are received, then no alerts are lost (at-least-once delivery).
3. Given alert schema is invalid, when signal arrives, then it is routed to DLQ with error context.
4. When the system is offline, then alerts queue locally for replay when connectivity returns.

## Implementation Plan

- Create Kafka topic `alerts.incoming` with 12 partitions, 7-day retention.
- Configure compacted topic `alerts.state` for dedup.
- Add alert producer script with retry/backup.
- Add Grafana dashboard for alert throughput metrics.

## Files

- `scripts/kafka-produce-alert.py` (new)
- `scripts/steps/19-kafka-alert-ingestion.py` (new)
- `gitops/kafka/base/kafka-alerts.yaml` (new)
- `gitops/kafka/overlays/dev/kustomization.yaml` (new)
- `gitops/monitoring/base/kafka-alert-dashboard.json` (new)
- `tests/test_kafka_alert_ingest.py` (new)