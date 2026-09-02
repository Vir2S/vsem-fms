import argparse
from getpass import getpass
import secrets

from vsem_fms.app.core.api_keys import hash_api_key


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or hash a secret for the API_KEYS registry.")
    parser.add_argument("secret", nargs="?", help="Existing API key secret to hash (minimum 16 characters)")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate a new high-entropy API key and print it together with its SHA-256 hash",
    )
    args = parser.parse_args()

    if args.generate and args.secret is not None:
        parser.error("secret and --generate cannot be used together")

    if args.generate:
        secret = f"fms_live_{secrets.token_urlsafe(36)}"
        print(f"secret={secret}")
        print(f"sha256={hash_api_key(secret)}")
        return

    secret = args.secret if args.secret is not None else getpass("API key secret: ")
    if len(secret) < 16:
        parser.error("secret must be at least 16 characters long")
    print(hash_api_key(secret))


if __name__ == "__main__":
    main()
