#!/usr/bin/env python3
"""Fail release checks on secrets, private paths, PII, or unsafe archives."""

from __future__ import annotations

import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "dist", "__pycache__", ".venv", "venv"}
MAX_TEXT_BYTES = 2_000_000
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "OpenAI key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Stripe live key": re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
    "npm token": re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"),
    "PyPI token": re.compile(r"\bpypi-[A-Za-z0-9_-]{20,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "Bearer token": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{20,}\b", re.IGNORECASE),
    "URL credentials": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
}
PRIVATE_HOME_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+|/(?:home|Users)/[^/\s]+)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
CN_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def findings_for_text(label: str, text: str) -> list[str]:
    findings = []
    for kind, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{label}: possible {kind}")
    if PRIVATE_HOME_RE.search(text):
        findings.append(f"{label}: possible private user-home path")
    if str(ROOT) in text or ROOT.as_posix() in text:
        findings.append(f"{label}: current absolute repository path")
    if EMAIL_RE.search(text):
        findings.append(f"{label}: email address requires privacy review")
    if CN_PHONE_RE.search(text):
        findings.append(f"{label}: phone number requires privacy review")
    return findings


def scan_source() -> tuple[int, list[str]]:
    scanned = 0
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or set(path.relative_to(ROOT).parts) & SKIP_DIRS:
            continue
        if path.stat().st_size > MAX_TEXT_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        findings.extend(findings_for_text(path.relative_to(ROOT).as_posix(), text))
    return scanned, findings


def scan_archives() -> tuple[int, list[str]]:
    scanned = 0
    findings = []
    for archive_path in sorted((ROOT / "dist").glob("*.skill")):
        with zipfile.ZipFile(archive_path) as archive:
            corrupt = archive.testzip()
            if corrupt:
                findings.append(f"{archive_path.name}: corrupt member {corrupt}")
            seen = set()
            for info in archive.infolist():
                name = info.filename
                pure = PurePosixPath(name)
                if name in seen:
                    findings.append(f"{archive_path.name}: duplicate member {name}")
                seen.add(name)
                if pure.is_absolute() or ".." in pure.parts:
                    findings.append(f"{archive_path.name}: unsafe member path {name}")
                if stat.S_ISLNK(info.external_attr >> 16):
                    findings.append(f"{archive_path.name}: symbolic link member {name}")
                if (
                    "/evals/" in f"/{name}/"
                    or "/__pycache__/" in f"/{name}/"
                    or "/.git/" in f"/{name}/"
                    or name.endswith((".pyc", ".pyo"))
                ):
                    findings.append(f"{archive_path.name}: forbidden member {name}")
                if info.is_dir() or info.file_size > MAX_TEXT_BYTES:
                    continue
                try:
                    text = archive.read(info).decode("utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                scanned += 1
                findings.extend(findings_for_text(f"{archive_path.name}:{name}", text))
    return scanned, findings


def main() -> int:
    source_count, source_findings = scan_source()
    archive_count, archive_findings = scan_archives()
    findings = source_findings + archive_findings
    print(f"Security scan: {source_count} source files, {archive_count} archive members")
    if findings:
        print("Security scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Security scan passed: no secrets, private paths, PII, or unsafe archive members detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
