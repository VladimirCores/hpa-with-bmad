#!/usr/bin/env python3
"""
CI script for Trivy vulnerability scanning of container images.

Usage:
    python3 trivy-scan-ci.py <image-reference> [--severity SEVERITY] [--exit-code CODE]

Example:
    python3 trivy-scan-ci.py myapp:1.0.0 --severity HIGH,CRITICAL --exit-code 1
"""

import argparse
import subprocess
import sys
import os


def run_trivy_scan(image: str, severity: str = "HIGH,CRITICAL", exit_code: int = 1) -> int:
    """
    Run Trivy vulnerability scan on a container image.
    
    Args:
        image: Container image reference (e.g., 'myapp:1.0.0' or 'localhost:5000/myapp:1.0.0')
        severity: Comma-separated list of severity levels to fail on (default: HIGH,CRITICAL)
        exit_code: Exit code to return if vulnerabilities are found (default: 1)
    
    Returns:
        0 if scan passes, exit_code if vulnerabilities found
    """
    cmd = [
        "trivy",
        "image",
        f"--exit-code={exit_code}",
        f"--severity={severity}",
        image
    ]
    
    print(f"Running Trivy scan on {image}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode != 0:
            print(f"❌ Trivy scan failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode
        
        print(f"✅ Trivy scan passed for {image}")
        return 0
        
    except FileNotFoundError:
        print("❌ Trivy not found. Please install Trivy or ensure it's in PATH.", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ Error running Trivy scan: {e}", file=sys.stderr)
        return 2


def main():
    parser = argparse.ArgumentParser(
        description="CI script for Trivy vulnerability scanning"
    )
    parser.add_argument(
        "image",
        help="Container image reference to scan (e.g., myapp:1.0.0)"
    )
    parser.add_argument(
        "--severity",
        default="HIGH,CRITICAL",
        help="Comma-separated severity levels to fail on (default: HIGH,CRITICAL)"
    )
    parser.add_argument(
        "--exit-code",
        type=int,
        default=1,
        help="Exit code to return if vulnerabilities found (default: 1)"
    )
    
    args = parser.parse_args()
    
    exit_code = run_trivy_scan(args.image, args.severity, args.exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()