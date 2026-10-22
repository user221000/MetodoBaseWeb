"""One explicit operator run; cron belongs to the deployment's operator."""
import argparse
import json
import logging
from pathlib import Path


class ReconciliationArgumentParser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("Invalid reconciliation arguments")


def main(argv=None):
    parser = ReconciliationArgumentParser(description="Reconcile only resources from a private operator manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--apply", action="store_true", help="Read provider truth and commit; default is local plan only")
    parser.add_argument("--max-items", type=int, default=25)
    parser.add_argument("--deadline-seconds", type=float, default=60)
    parser.add_argument("--cursor")
    try:
        args = parser.parse_args(argv)
        from web.services.billing_reconciliation import MAX_MANIFEST_BYTES, run
        with Path(args.manifest).open("rb") as source:
            manifest = source.read(MAX_MANIFEST_BYTES + 1)
        result = run(manifest, apply=args.apply, cursor=args.cursor,
            max_items=args.max_items, seconds=args.deadline_seconds)
    except (OSError, ValueError):
        print(json.dumps({"code": "reconciliation_invalid_input"}))
        return 64
    except Exception as error:  # noqa: BLE001 -- CLI never serializes unknown exception payloads or claims success.
        logging.getLogger(__name__).error("reconciliation_unconfirmed class=%s", type(error).__name__)
        print(json.dumps({"code": "reconciliation_unconfirmed"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    if result["unconfirmed"]:
        return 2
    if result["retryable"] or result["deferred"]:
        return 75
    return 3 if result["manual"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
