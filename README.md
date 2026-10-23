# DataMerge Studio

A minimal spreadsheet consolidation prototype built with Python, Pandas, Streamlit, OpenPyXL, and Pytest.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

Open http://localhost:8501 for local development. Source code: [nicanorjrequena/datamerge-studio](https://github.com/nicanorjrequena/datamerge-studio).

**Live app:** [Open DataMerge Studio](https://datamerge-studio-foargqfdcmighktrnyvpca.streamlit.app/). The hosted URL returns HTTP 200 and serves the Streamlit page; interactive hosted acceptance testing remains pending.

## Try the two-minute demonstration

Upload the two synthetic CSV files in [data/recruiter_demo](data/recruiter_demo). Follow the short workflow there to match order-number headers, drop Internal Note, and export five records with four columns. The [verified expected CSV](docs/examples/recruiter-master.csv) is included for comparison. No demonstration files load automatically.

## Current workflow

1. **Upload:** Add up to 10 CSV/XLSX files. **Clear data**, above the uploader, removes all uploaded files, worksheet selections, and column edits from the current session. A single-sheet workbook needs no extra decision; for multi-sheet workbooks, expand the worksheet checklist to choose what to include (all are selected initially). Remove or replace individual files using the uploader. Click **Next: Review data**.
2. **Data Mapping / Review:** Expand a file to preview its first 10 records; Excel has a separate collapsed preview for each selected worksheet. All panels start closed. The output preview shows the result below. Optionally expand **Match or drop columns**, select equivalent names, choose the name to keep, and click **Treat as the same column**. Select unwanted fields and click **Drop column** to omit them from output. **Undo last change** reverses the last action. Click **Next: Export**.
3. **Export:** Choose CSV or Excel and download the consolidated file. Excel contains one Master worksheet.

The application starts without datasets. It appends records vertically, aligning identical detected header names and explicitly matched names. Other headers remain separate. Column order follows first appearance; missing fields are blank. Data types are not converted by consolidation. Duplicate records and source row order are retained. Every step shows input/output row reconciliation. Back buttons and the sidebar preserve selected data and column changes. Editing uploads or worksheet selections clears column changes with a notice, so prior choices are not applied to new inputs. No synonym approval, schema editor, header-range controls, templates, or report downloads are exposed.

Matching changes only the output: it never modifies source files or concatenates cell values. Columns that coexist in a single selected dataset cannot be matched because this could overwrite values. Dropping columns retains all rows, even if a particular dataset then contributes only blank values; the last output column cannot be dropped.

## Limitations

- The first populated row is treated as the header. Whitespace in names is normalized. Blank or duplicate names block the file; repair the source before uploading. Multi-row headers cannot be configured in this reduced interface.
- Only selected Excel sheets are included, in workbook order. An empty/corrupt selected sheet or invalid file blocks export with a source-specific message. Correct or remove the affected workbook, or deselect an unwanted sheet. Selecting zero sheets blocks that workbook until resolved.
- CSV must be comma-delimited UTF-8, with or without BOM. Entirely blank records are excluded; partially populated records remain.
- Duplicate filenames (case-insensitive) and byte-identical uploads, including renamed copies, are flagged and block export until removed. No file is silently discarded. Different file encodings or separately saved workbooks with equivalent records are not detected as duplicate uploads; duplicate data rows remain in output.
- There is no record-count cap and no practical application file-size cap. Streamlit requires a finite upload setting, configured to 2,147,483,647 MB. Available memory and hosting constraints still apply. All data is processed in memory and reparsed on interaction; this is not a streaming implementation.
- Excel output is limited to 1,048,575 data rows plus its header and 16,384 columns. Larger output must use CSV.
- Excel formula-like text is stored as text. CSV preserves raw values, which spreadsheet applications can interpret as formulas.
- No relational joins, persistent storage, accounts, external integrations, or machine learning.
- Use non-confidential files. Application code does not intentionally write uploads to disk.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

See [test results](docs/test_results.md) and [architecture](docs/architecture.md). Historical benchmark artifacts measure an earlier engine workflow and are not current application performance claims.

The current release candidate passes **62 automated tests**. Direct dependencies are pinned to the locally verified versions in `requirements.txt`.

Synthetic port reports under `data/demo` are regression fixtures, not automatic application defaults. Local `Sample Data` remains excluded from Git. No employer data is required.

## Deployment handoff

The source is published at [nicanorjrequena/datamerge-studio](https://github.com/nicanorjrequena/datamerge-studio) on branch `main`. The live app URL above is reachable. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the hosted acceptance checklist. Screenshots and interactive hosted browser acceptance testing remain pending.
