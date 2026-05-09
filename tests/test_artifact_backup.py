from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from stock_watch.cli.artifact_backup import collect_backup_files
from stock_watch.cli.artifact_backup import main


class ArtifactBackupTests(unittest.TestCase):
    def test_collect_backup_files_skips_cache_and_logs_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            theme = root / "theme"
            verification = root / "verification"
            (theme / "logs").mkdir(parents=True)
            (theme / "history_cache").mkdir()
            verification.mkdir()
            (verification / "yfinance_cache").mkdir()
            (theme / "daily_rank.csv").write_text("ticker\n2330.TW\n", encoding="utf-8")
            (theme / "logs" / "2330_TW.csv").write_text("x\n", encoding="utf-8")
            (theme / "history_cache" / "2330.csv").write_text("x\n", encoding="utf-8")
            (verification / "reco_snapshots.csv").write_text("ticker\n2330.TW\n", encoding="utf-8")
            (verification / "yfinance_cache" / "2330.csv").write_text("x\n", encoding="utf-8")

            files = collect_backup_files(theme_outdir=theme, verification_outdir=verification)

        archive_paths = {item.archive_path for item in files}
        self.assertEqual(archive_paths, {"theme/daily_rank.csv", "verification/reco_snapshots.csv"})

    def test_main_creates_zip_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            theme = root / "theme"
            verification = root / "verification"
            backup_dir = root / "backups"
            manifest_json = root / "manifest.json"
            manifest_md = root / "manifest.md"
            theme.mkdir()
            verification.mkdir()
            (theme / "daily_report.md").write_text("# report\n", encoding="utf-8")
            (verification / "reco_outcomes.csv").write_text("ticker\n2330.TW\n", encoding="utf-8")

            code = main(
                [
                    "--theme-outdir",
                    str(theme),
                    "--verification-outdir",
                    str(verification),
                    "--backup-dir",
                    str(backup_dir),
                    "--manifest-json",
                    str(manifest_json),
                    "--manifest-md",
                    str(manifest_md),
                    "--name",
                    "safe.zip",
                ]
            )
            payload = json.loads(manifest_json.read_text(encoding="utf-8"))
            backup_path = Path(payload["backup_path"])

            with zipfile.ZipFile(backup_path) as archive:
                names = set(archive.namelist())

            self.assertEqual(code, 0)
            self.assertTrue(backup_path.exists())
            self.assertEqual(payload["mode"], "backup")
            self.assertEqual(payload["file_count"], 2)
            self.assertIn("theme/daily_report.md", names)
            self.assertIn("verification/reco_outcomes.csv", names)
            self.assertTrue(manifest_md.exists())

    def test_main_dry_run_writes_manifest_without_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            theme = root / "theme"
            verification = root / "verification"
            manifest_json = root / "manifest.json"
            manifest_md = root / "manifest.md"
            theme.mkdir()
            verification.mkdir()
            (theme / "daily_rank.csv").write_text("ticker\n2330.TW\n", encoding="utf-8")

            code = main(
                [
                    "--theme-outdir",
                    str(theme),
                    "--verification-outdir",
                    str(verification),
                    "--manifest-json",
                    str(manifest_json),
                    "--manifest-md",
                    str(manifest_md),
                    "--dry-run",
                ]
            )
            payload = json.loads(manifest_json.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(payload["backup_path"], "")
        self.assertEqual(payload["file_count"], 1)
