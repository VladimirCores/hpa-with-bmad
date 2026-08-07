# Story 9-2: Enable Agent-to-Agent Communication

Status: done

Baseline commit: dc46f56

## Story

As an AI Agent,
I want authenticated agent-to-agent messaging,
So that coordinated decision-making and task delegation can happen without unauthorized impersonation.

## Acceptance Criteria

1. Given agents are registered with the platform, when one agent sends a message to another, then the message is routed through an authenticated channel.
2. Given an unregistered sender, when a message is sent, then unauthorized impersonation is prevented.
3. Given registered agents, when discovery is performed, then agent registration and discovery work as configured.
4. Given the process runs offline, when it completes, then no internet access is required.
5. Given a failure, when the script runs, then it exits with a non-zero status on failure.

## Implementation Plan

- Add `gitops/agent-engine/base/a2a.yaml` binding the `AgentCommunication` contract (registered agents required, authenticated channel, unauthorized impersonation prevented, registered-agents-only discovery).
- Add A2A broker deployment, agent registry ConfigMap, and message routing config.
- Install script with `--check` / `--dry-run` / `--apply`, step wrapper, and validation test.

## Files

- `gitops/agent-engine/base/a2a.yaml` (new)
- `gitops/agent-engine/overlays/dev/kustomization.yaml` (updated to include `a2a.yaml`)
- `scripts/install-a2a-dev.py` (new)
- `scripts/steps/44-install-a2a-dev.py` (new)
- `tests/test_install_a2a_dev.py` (new)
