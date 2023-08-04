"""Get the version from manifest.json."""
from __future__ import annotations

import json
import sys


def main():
    """Main function to get the version from manifest.json."""  # noqa: D401
    with open("./custom_components/ipv64/manifest.json", encoding="utf-8") as json_file:
        data = json.load(json_file)
        print(data["version"])  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
