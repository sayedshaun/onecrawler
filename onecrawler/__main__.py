import argparse
import sys

from .version import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="onecrawler",
        description=(
            "OneCrawler is an async Python crawling framework used as a library, "
            "not a standalone CLI. Import it in your own scripts, e.g.:\n\n"
            "    import onecrawler\n"
            "    crawler = onecrawler.Crawler(...)\n\n"
            "See https://sayedshaun.github.io/onecrawler/ for usage examples."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"onecrawler {__version__}"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        return

    parser.parse_args()


if __name__ == "__main__":
    main()
