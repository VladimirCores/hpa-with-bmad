#!/usr/bin/env python3
"""Trigger alert responses via Kubernetes Job execution.

This script evaluates alert conditions and triggers predefined
Kubernetes Jobs to remediate incidents automatically.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DEF = ROOT / "gitops" / "alerts" / "base" / "alert-workflows.yaml"


def load_workflows() -> dict[str, Any]:
    if not WORKFLOW_DEF.exists():
        raise RuntimeError(f"Workflow definition not found: {WORKFLOW_DEF}")
    return yaml.safe_load(WORKFLOW_DEF.read_text(encoding="utf-8"))


def validate_workflow(alert: dict, workflow: dict) -> bool:
    trigger = workflow.get("trigger", {})
    if alert.get("severity") != trigger.get("severity"):
        return False
    if alert.get("alert_type") != trigger.get("alert_type"):
        return False
    return True


def execute_kubernetes_job(action: dict, alert: dict, dry_run: bool) -> int:
    action_type = action.get("type")
    target_selector = action.get("target_selector", "")

    context = alert.get("context", {})
    replace_map = {
        "deployment": context.get("deployment_name", "unknown"),
        "namespace": context.get("namespace", "default"),
        "hpa_name": context.get("hpa_name", "unknown"),
        "replicas": context.get("current_replicas", 1),
        "pod_name": context.get("pod_name", "unknown"),
        "node_name": context.get("node_name", "unknown"),
    }

    if dry_run:
        print(f"[DRY-RUN] Would execute {action_type}")
        print(f"  Target selector: {target_selector}")
        print(f"  Context: {json.dumps(alert.get('context', {}), indent=2)}")
        return 0

    cmd = ["kubectl", "apply", "-f", "-"]
    job_yaml = build_job_yaml(action_type, target_selector, replace_map)

    try:
        result = subprocess.run(cmd, input=job_yaml, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Job execution failed: {result.stderr}", file=sys.stderr)
            return 1
        print(f"Job executed: {action_type}")
        return 0
    except FileNotFoundError:
        print("kubectl not found", file=sys.stderr)
        return 1


def build_job_yaml(action_type: str, selector: str, context: dict) -> str:
    job_name = f"alert-action-{action_type}"
    container_cmd = build_container_command(action_type, selector, context)

    return f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: {job_name}
  namespace: {context.get('namespace', 'default')}
spec:
  backoffLimit: 2
  template:
    spec:
      serviceAccountName: alert-response-trigger
      containers:
        - name: executor
          image: bitnami/kubectl:latest
          command: ["/bin/sh", "-c"]
          args:
            - |
{container_cmd}
      restartPolicy: Never
"""


def build_container_command(action_type: str, selector: str, context: dict) -> str:
    if action_type == "restart_deployment":
        return f'''echo "Restarting deployment: {selector}" && kubectl rollout restart deployment/{context.get('deployment', 'unknown')} -n {context.get('namespace', 'default')}'''
    elif action_type == "scale_deployment":
        return f'''echo "Scaling deployment: {selector}" && kubectl scale deployment/{context.get('deployment', 'unknown')} --replicas={context.get('replicas', 1)} -n {context.get('namespace', 'default')}'''
    elif action_type == "delete_pod":
        return f'''echo "Deleting pod: {selector}" && kubectl delete pod {context.get('pod_name', 'unknown')} -n {context.get('namespace', 'default')}'''
    else:
        return f'''echo "Unknown action: {action_type}"'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger alert responses")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    parser.add_argument("alert_json", help="Alert signal as JSON")
    args = parser.parse_args()

    try:
        alert = json.loads(args.alert_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    workflows = load_workflows()
    spec = workflows.get("spec", {})
    workflow_list = spec.get("workflows", [])

    matching = next((wf for wf in workflow_list if validate_workflow(alert, wf)), None)
    if matching is None:
        print(
            f"No matching workflow for alert: {alert.get('alert_type')} ({alert.get('severity')})",
            file=sys.stderr,
        )
        return 1

    for action in matching.get("actions", []):
        if execute_kubernetes_job(action, alert, args.dry_run) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())