# High Performance Distributed Cluster (HPDC)

HPDC is an offline-first, security-focused distributed cluster scaffold for Talos, Cilium, and Rook-Ceph.

## Project-wide scripting rule

All project automation scripts must be written in Python 3. Shell wrappers are not allowed in the project `scripts/` directory.

## Bootstrap

Run:

```python
scripts/bootstrap-dev.py
```

Expected output:

```text
HPDC scaffold created.
```

The bootstrap command creates the standard monorepo layout and platform scaffold. Continue with Story 1.2 to provision the offline Talos dev cluster.
