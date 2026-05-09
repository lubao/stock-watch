This directory is for generated local stock-watch run artifacts.

The workflow writes daily reports, rank CSVs, alert tracking, runtime metrics, logs, caches, and research reports here. These outputs are intentionally ignored by git by default to keep code and research commits clean.

If a run result must be preserved in repository history, create an explicit artifact snapshot commit with `git add -f` for the selected files only.
