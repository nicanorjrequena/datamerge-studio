# Simplified interface — verification

Command: `.venv/Scripts/python -m pytest -q`

Result: **61 passed** locally on Python 3.11.9. `python -m pip check` also reports no broken requirements. Direct dependencies are pinned to Streamlit 1.66.1, Pandas 2.3.3, OpenPyXL 3.1.5, and Pytest 9.1.1.

The reduced workflow tests verify:

- Empty starting state; Upload is the initial page.
- Data Mapping shows per-file previews (and nested worksheet previews for Excel) in panels that start closed, optional match/drop actions, and a first-10-record output preview.
- CSV/XLSX format selection and one corresponding master download.
- Exact-name alignment, different names kept separate, first-seen column order, null padding, source row order, duplicate retention, and reconciled row counts.
- All worksheets included from a controlled workbook.
- File-specific errors, unsupported formats, duplicate filenames, and the 10-file limit.
- CSV and single-Master-sheet Excel outputs can be reopened with the expected records.
- Excel formula-like text remains text; oversized Excel output prompts use of CSV.
- Uploaded inputs persist when navigating between sections.
- Duplicate filenames are flagged case-insensitively; renamed byte-identical uploads are flagged with both filenames, and export is blocked. Duplicate data records within legitimate inputs remain preserved.
- Explicit equivalent-name matching, retaining the chosen name, column dropping, and undo preserve original data, duplicate records, and all input rows. CSV and Excel are reopened and checked for expected edited values.
- Matching coexisting fields, dropping all output columns, and invalid selections are blocked without mutating sources or applying history.
- Next/Back navigation preserves edits; worksheet selection persists and controls the output. Changing selected sheets clears prior edits. Single-sheet files need no sheet checklist; empty/invalid selections block processing.
- The recruiter demo has 2 synthetic CSVs, 5 input/output rows, 4 columns after matching and dropping, and quantity total 455. Its checked-in expected master CSV is compared with the actual engine result.

Release inspection corrected an intermittent fixture issue: the worksheet-selection UI test now uses fixed Excel bytes on every rerun. Recreating a ZIP-based workbook each rerun could change its timestamps and incorrectly simulate a new upload. Production file fingerprint behavior remains unchanged.

Existing unit regression tests for underlying legacy loading, multi-row headers, mapping, grouping, templates, and validation still pass. These are library regression tests, not a claim that those controls remain available in the current interface. Tests for removed interactions were replaced with reduced-workflow acceptance tests.

Streamlit AppTest was used for interface verification. No public deployment, real-browser end-to-end test, or new performance benchmark was performed for this change.
