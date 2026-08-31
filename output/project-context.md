---
project_name: 'High Performance Distributed Cluster (HPDC)'
user_name: 'Master'
date: '2026-08-18'
sections_completed: ['technology_stack']
existing_patterns_found: 12
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

_Technology stack details available in project README._

## Critical Implementation Rules

### Config Layer System (Three-File Split)

The project uses a three-layer configuration system loaded by `component_versions.load_all_dotenv()`:

1. **`.env`** — Provisioning & sizing only: `HPDC_PROVIDER`, `HPDC_CONTROLPLANES`, `HPDC_WORKERS`, `HPDC_CPUS_*`, `HPDC_MEMORY_*`, `HPDC_DISK_CAPACITY_*`, `HPDC_SUBNET`, `HPDC_DISKS`
2. **`.env.components`** — Feature toggles: `HPDC_*_ENABLED` flags, `HPDC_STORAGE_BACKEND`
3. **`.env.versions`** — Version pins: `HPDC_*_VERSION`, `HPDC_*_CHART_VERSION`, `HPDC_*_TAG`

**Loading order:** `.env` → `.env.components` → `.env.versions` (setdefault semantics — existing env wins).

**Rules:**
- All bootstrap scripts must call `component_versions.load_all_dotenv()` — never read `.env` directly with `open()`/`read_text()`
- New variables must go in exactly one layer; grep to verify no cross-layer duplication
- `HPDC_STORAGE_BACKEND` lives in `.env.components` (not provisioning) despite affecting storage behavior