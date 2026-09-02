#!/usr/bin/env python3
"""
CI script for Cosign container image signing.

Usage:
    python3 cosign-sign-ci.py <image-reference> [--key KEY_PATH]

Example:
    python3 cosign-sign-ci.py localhost:5000/myapp:1.0.0 --key /path/to/cosign.key
"""

import argparse
import subprocess
import sys
import os


def run_cosign_sign(image: str, key_path: str = None) -> int:
    """
    Run Cosign signing on a container image.
    
    Args:
        image: Container image reference (e.g., 'localhost:5000/myapp:1.0.0')
        key_path: Path to the Cosign private key (optional, uses keyless if not provided)
    
    Returns:
        0 if signing succeeds, non-zero otherwise
    """
    cmd = ["cosign", "sign"]
    
    if key_path:
        cmd.extend(["--key", key_path])
    
    cmd.append(image)
    
    print(f"Signing {image} with Cosign...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        if result.returncode != 0:
            print(f"❌ Cosign signing failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode
        
        print(f"✅ Cosign signing successful for {image}")
        return 0
        
    except FileNotFoundError:
        print("❌ Cosign not found. Please install Cosign or ensure it's in PATH.", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ Error running Cosign sign: {e}", file=sys.stderr)
        return 2


def main():
    parser = argparse.ArgumentParser(
        description="CI script for Cosign container image signing"
    )
    parser.add_argument(
        "image",
        help="Container image reference to sign (e.g., localhost:5000/myapp:1.0.0)"
    )
    parser.add_argument(
        "--key",
        help="Path to Cosign private key (optional, uses keyless if not provided)"
    )
    
    args = parser.parse_args()
    
    # Get key from environment variable if not provided
    key_path = args.key or os.environ.get("COSIGN_KEY")
    
    exit_code = run_cosign_sign(args.image, key_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()