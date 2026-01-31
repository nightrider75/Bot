#!/usr/bin/env python3
"""
TURN Credential Generator

Generate time-limited TURN credentials for WebRTC.
Usage: python3 generate_turn_credentials.py --secret YOUR_SECRET
"""

import hmac
import hashlib
import time
import base64
import argparse


def generate_turn_credentials(secret: str, username: str = "webrtc-user", ttl: int = 86400) -> dict:
    """Generate time-limited TURN credentials compatible with coturn."""
    timestamp = int(time.time()) + ttl
    turn_username = f"{timestamp}:{username}"
    
    turn_password = base64.b64encode(
        hmac.new(
            secret.encode('utf-8'),
            turn_username.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')
    
    return {
        "username": turn_username,
        "credential": turn_password,
        "ttl_hours": ttl / 3600
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TURN credentials")
    parser.add_argument("--secret", required=True, help="TURN server secret")
    parser.add_argument("--username", default="webrtc-user", help="Username prefix")
    parser.add_argument("--ttl", type=int, default=86400, help="TTL in seconds (default: 86400 = 24h)")
    
    args = parser.parse_args()
    creds = generate_turn_credentials(args.secret, args.username, args.ttl)
    
    print("=" * 70)
    print("TURN Server Credentials")
    print("=" * 70)
    print(f"Username:   {creds['username']}")
    print(f"Credential: {creds['credential']}")
    print(f"Valid for:  {creds['ttl_hours']:.1f} hours")
    print("=" * 70)
    print("\nEnvironment Variables:")
    print(f"export WEBRTC_TURN_USERNAME='{creds['username']}'")
    print(f"export WEBRTC_TURN_CREDENTIAL='{creds['credential']}'")
    print("=" * 70)
