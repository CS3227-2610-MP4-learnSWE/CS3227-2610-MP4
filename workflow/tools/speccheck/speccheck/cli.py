"""Command line: argument parsing, folder discovery, output and exit code."""

import argparse
import sys
from pathlib import Path

from .registry import RULES
from .rules import Finding, check_spec_dir
from .waivers import Waiver, WaiverError, load_waivers

WAIVER_FILE = "speccheck-waivers.txt"
DEFAULT_SPECS_DIR = Path(__file__).resolve().parents[3] / "specs"


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _UsageError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="speccheck", add_help=False, allow_abbrev=False)
    parser.add_argument("--specs-dir")
    parser.add_argument("--waivers")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list-rules", action="store_true")
    parser.add_argument("dirs", nargs="*")
    return parser


def _emit(stream, text: str) -> None:
    encoding = getattr(stream, "encoding", None) or "utf-8"
    print(text.encode(encoding, errors="backslashreplace").decode(encoding), file=stream)


def _yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def _rule_line(rule) -> str:
    return (
        f'RULE {rule.id} tier={rule.tier} file={rule.file} where="{rule.where}" '
        f'skip_no_screen={_yes_no(rule.skip_no_screen)} '
        f'skip_added_items={_yes_no(rule.skip_added_items)} source="{rule.source}"'
    )


def _finding_line(f: Finding) -> str:
    return f'FAIL {f.spec_id} {f.file}: section "{f.heading}": {f.message} [{f.code}]'


def _folders(args, specs_dir: Path) -> list[Path]:
    if args.all:
        if not specs_dir.is_dir():
            raise _UsageError(f"specs dir not found: {specs_dir}")
        return sorted(p for p in specs_dir.iterdir() if p.is_dir())
    folders = {}
    for name in args.dirs:
        folder = Path(name)
        if not folder.is_dir():
            raise _UsageError(f"not a folder: {name}")
        folders[folder.resolve()] = None
    return sorted(folders, key=lambda p: p.name)


def _waivers(args, specs_dir: Path) -> dict[str, Waiver]:
    path = Path(args.waivers) if args.waivers else specs_dir / WAIVER_FILE
    try:
        return load_waivers(path)
    except FileNotFoundError:
        if args.waivers:
            raise _UsageError(f"waiver file not found: {path}")
        return {}
    except OSError as error:
        raise _UsageError(f"cannot read waiver file {path}: {error.strerror}")
    except WaiverError as error:
        raise _UsageError(f"{path}: line {error.line}: {error.message} [WAIVER_BAD_LINE]")


def _check_all(folders: list[Path], waivers: dict[str, Waiver]) -> tuple[list[str], int, int, int]:
    lines, failed, waived = [], 0, 0
    for folder in folders:
        waiver = waivers.get(folder.name)
        if waiver:
            lines.append(f"WAIVED {folder.name} ({waiver.scope}): {waiver.reason}")
        if waiver and waiver.scope == "all":
            waived += 1
            continue
        findings = check_spec_dir(folder, waivers)
        failed += bool(findings)
        lines += [_finding_line(f) for f in findings] or [f"OK {folder.name}"]
    return lines, len(folders) - waived, failed, waived


def _run(args) -> tuple[list[str], int]:
    if args.list_rules:
        if args.all or args.dirs:
            raise _UsageError("--list-rules cannot be combined with folders or --all")
        return [_rule_line(rule) for rule in RULES], 0
    if args.all == bool(args.dirs):
        raise _UsageError("give spec folders, or --all, or --list-rules")
    specs_dir = Path(args.specs_dir) if args.specs_dir else DEFAULT_SPECS_DIR
    folders = _folders(args, specs_dir)
    waivers = _waivers(args, specs_dir)
    lines, checked, failed, waived = _check_all(folders, waivers)
    if args.all:
        known = {folder.name for folder in folders}
        lines += [
            f"WARN {spec_id}: waiver for a spec folder that does not exist [WAIVER_UNKNOWN_ID]"
            for spec_id in sorted(set(waivers) - known)
        ]
    lines.append(f"speccheck: {checked} checked, {failed} failed, {waived} waived")
    return lines, failed


def main(argv: list[str]) -> int:
    """Run the checker; findings go to stdout, usage and waiver errors to stderr."""
    try:
        lines, failed = _run(_parser().parse_args(argv))
    except _UsageError as error:
        _emit(sys.stderr, f"speccheck: error: {error}")
        return 2
    for line in lines:
        _emit(sys.stdout, line)
    return 1 if failed else 0
