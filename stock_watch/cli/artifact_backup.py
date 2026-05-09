from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from stock_watch.paths import REPO_ROOT
from stock_watch.paths import THEME_OUTDIR
from stock_watch.paths import VERIFICATION_OUTDIR

DEFAULT_BACKUP_DIR = REPO_ROOT / "runs" / "artifact_backups"
DEFAULT_MANIFEST_JSON = THEME_OUTDIR / "artifact_backup_manifest.json"
DEFAULT_MANIFEST_MD = THEME_OUTDIR / "artifact_backup_manifest.md"

EXCLUDED_DIR_NAMES = {
    ".yfinance_cache",
    "__pycache__",
    "history_cache",
    "local_site",
    "logs",
    "yfinance_cache",
}
EXCLUDED_FILE_NAMES = {
    "README.md",
    "artifact_backup_manifest.json",
    "artifact_backup_manifest.md",
}


@dataclass(frozen=True)
class BackupFile:
    source_root: str
    path: str
    archive_path: str
    size_bytes: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local backup zip for generated stock-watch run artifacts.")
    parser.add_argument("--theme-outdir", default=str(THEME_OUTDIR))
    parser.add_argument("--verification-outdir", default=str(VERIFICATION_OUTDIR))
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    parser.add_argument("--manifest-json", default=str(DEFAULT_MANIFEST_JSON))
    parser.add_argument("--manifest-md", default=str(DEFAULT_MANIFEST_MD))
    parser.add_argument("--name", default="", help="Optional backup file stem. Defaults to timestamped stock_watch_artifacts.")
    parser.add_argument("--dry-run", action="store_true", help="Build the manifest but do not create the zip file.")
    parser.add_argument("--include-cache", action="store_true", help="Include cache directories such as history_cache and yfinance_cache.")
    parser.add_argument("--include-logs", action="store_true", help="Include per-ticker log directories.")
    return parser.parse_args(argv)


def _should_skip(path: Path, *, include_cache: bool, include_logs: bool) -> bool:
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    parts = set(path.parts)
    if not include_logs and "logs" in parts:
        return True
    if include_cache:
        return False
    return bool(parts.intersection(EXCLUDED_DIR_NAMES - {"logs"}))


def collect_backup_files(
    *,
    theme_outdir: Path = THEME_OUTDIR,
    verification_outdir: Path = VERIFICATION_OUTDIR,
    include_cache: bool = False,
    include_logs: bool = False,
) -> list[BackupFile]:
    roots = [
        ("theme", theme_outdir),
        ("verification", verification_outdir),
    ]
    files: list[BackupFile] = []
    for source_root, root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if _should_skip(relative, include_cache=include_cache, include_logs=include_logs):
                continue
            archive_path = Path(source_root) / relative
            files.append(
                BackupFile(
                    source_root=source_root,
                    path=str(path),
                    archive_path=archive_path.as_posix(),
                    size_bytes=int(path.stat().st_size),
                )
            )
    return files


def _default_backup_name(now: datetime) -> str:
    return f"stock_watch_artifacts_{now.strftime('%Y%m%d_%H%M%S')}.zip"


def create_backup_zip(*, files: list[BackupFile], backup_dir: Path, name: str, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_name = name.strip() if name.strip() else _default_backup_name(now)
    if not backup_name.endswith(".zip"):
        backup_name += ".zip"
    backup_path = backup_dir / backup_name
    with zipfile.ZipFile(backup_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.write(item.path, arcname=item.archive_path)
    return backup_path


def build_manifest(
    *,
    files: list[BackupFile],
    backup_path: Path | None,
    dry_run: bool,
    include_cache: bool,
    include_logs: bool,
    generated_at: str,
) -> dict[str, object]:
    total_size = sum(item.size_bytes for item in files)
    return {
        "generated_at": generated_at,
        "mode": "dry-run" if dry_run else "backup",
        "backup_path": str(backup_path) if backup_path is not None else "",
        "file_count": len(files),
        "total_size_bytes": total_size,
        "include_cache": include_cache,
        "include_logs": include_logs,
        "files": [asdict(item) for item in files],
    }


def render_manifest_markdown(manifest: dict[str, object]) -> str:
    lines = [
        "# Artifact Backup Manifest",
        f"- Generated: {manifest.get('generated_at', '')}",
        f"- Mode: `{manifest.get('mode', '')}`",
        f"- Backup path: `{manifest.get('backup_path', '') or 'n/a'}`",
        f"- File count: `{manifest.get('file_count', 0)}`",
        f"- Total size bytes: `{manifest.get('total_size_bytes', 0)}`",
        f"- Include cache: `{manifest.get('include_cache', False)}`",
        f"- Include logs: `{manifest.get('include_logs', False)}`",
        "",
        "## Files",
        "",
        "| Source | Size (bytes) | Archive Path | Local Path |",
        "| --- | --- | --- | --- |",
    ]
    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("source_root", "")),
                    str(item.get("size_bytes", 0)),
                    str(item.get("archive_path", "")).replace("|", "\\|"),
                    str(item.get("path", "")).replace("|", "\\|"),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_manifest(*, manifest: dict[str, object], manifest_json: Path, manifest_md: Path) -> None:
    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    manifest_md.parent.mkdir(parents=True, exist_ok=True)
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_md.write_text(render_manifest_markdown(manifest), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    files = collect_backup_files(
        theme_outdir=Path(args.theme_outdir),
        verification_outdir=Path(args.verification_outdir),
        include_cache=args.include_cache,
        include_logs=args.include_logs,
    )
    backup_path = None
    if not args.dry_run:
        backup_path = create_backup_zip(
            files=files,
            backup_dir=Path(args.backup_dir),
            name=str(args.name),
        )
    manifest = build_manifest(
        files=files,
        backup_path=backup_path,
        dry_run=args.dry_run,
        include_cache=args.include_cache,
        include_logs=args.include_logs,
        generated_at=generated_at,
    )
    write_manifest(manifest=manifest, manifest_json=Path(args.manifest_json), manifest_md=Path(args.manifest_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
