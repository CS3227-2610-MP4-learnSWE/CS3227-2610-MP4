"""Activate forward-only coverage only after all workers run instrumented code."""
import argparse

from ai_usage.service import activate_coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", action="append", choices=("STU-03", "TEA-02"), required=True)
    args = parser.parse_args()
    try:
        activate_coverage(args.feature)
    except Exception:
        parser.exit(1, "AI usage coverage could not be activated. Check database configuration and migrations.\n")
    print("AI usage coverage activated; existing starts and gaps preserved.")


if __name__ == "__main__":
    main()
