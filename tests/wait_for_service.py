#!/usr/bin/env python3
"""Poll a URL until it returns HTTP 200 or timeout is reached."""
import argparse
import sys
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    while True:
        try:
            requests.get(args.url, timeout=5)
            print(f"Service ready at {args.url}")
            return
        except requests.exceptions.ConnectionError:
            pass  # port not yet listening
        except Exception:
            pass  # any other response means port is up
        remaining = deadline - time.time()
        if remaining <= 0:
            print(f"Timed out after {args.timeout}s waiting for {args.url}", file=sys.stderr)
            sys.exit(1)
        print(f"  waiting... ({args.timeout - int(remaining)}s elapsed)")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
