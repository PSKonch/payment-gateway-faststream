import argparse
import json
import sys
from pathlib import Path
from typing import cast

from app.services import SignatureService


def read_body(args: argparse.Namespace) -> bytes:
    body_file = cast(str | None, args.body_file)
    if body_file:
        return Path(body_file).read_bytes()

    body = cast(str | None, args.body)
    if body is not None:
        return body.encode()

    return b""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate merchant auth signature headers")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--body", default=None)
    parser.add_argument("--body-file", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    body = read_body(args)
    canonical_request = SignatureService.build_canonical_request(args.method, args.path, body)
    signature = SignatureService.sign_canonical_request(canonical_request, args.secret)

    output = {
        "x-api-key": args.api_key,
        "x-signature": signature,
        "canonical_request": canonical_request,
        "body_sha256": SignatureService.body_sha256_hex(body),
    }

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
