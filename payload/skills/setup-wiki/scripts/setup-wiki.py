#!/usr/bin/env python3

import argparse
from pathlib import Path

from wiki_setup import scaffold_vault


def option_value(value):
    key, separator, option = value.partition("=")
    if not separator or not key.strip():
        raise argparse.ArgumentTypeError("options must use KEY=VALUE")
    return key.strip(), option.strip()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create or adopt a cross-project agent wiki vault."
    )
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--project", action="append", required=True, type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--option", action="append", default=[], type=option_value)
    return parser.parse_args()


def main():
    args = parse_args()
    result = scaffold_vault(
        args.vault,
        args.name,
        args.purpose,
        args.project,
        args.exclude,
        options=dict(args.option),
    )
    print(
        f"created={len(result.created)} "
        f"preserved={len(result.preserved)} "
        f"pointers={len(result.pointers)}"
    )


if __name__ == "__main__":
    main()
