"""Get the version from manifest.json."""  # noqa: INP001

from __future__ import annotations

import json
from pathlib import Path
import sys


def main():
    """Prints the version from custom_components/ipv64/manifest.json."""
    with Path("./custom_components/ipv64/manifest.json").open(encoding="utf-8") as json_file:
        data = json.load(json_file)
        print(data["version"])  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
