# Publishing handoff

Status: source published at https://github.com/nicanorjrequena/datamerge-studio on branch `main`. Hosted URL: https://datamerge-studio-foargqfdcmighktrnyvpca.streamlit.app/ . An HTTP session confirmed status 200 and the Streamlit page on October 22, 2026. This verifies endpoint reachability, not Python application execution or the interactive upload/download journey. Hosted browser acceptance testing remains pending. Use the current simplified workflow rather than earlier feature plans.

## GitHub

1. Create an empty repository named `datamerge-studio` under the intended GitHub account. Do not initialize another README if pushing this local repository.
2. Review the staged file list. Exclude `.venv`, `Sample Data`, logs, credentials, `.env` files, and `.streamlit/secrets.toml`.
3. Commit the reviewed application, tests, documentation, and synthetic demo files. Set the branch to `main`.
4. Add the actual repository URL as `origin` and push. Confirm that the README and synthetic demo files appear on GitHub.

## Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud with the GitHub account that can access the repository.
2. Create an app from that repository and branch, with `app.py` as the entry point.
3. Use Python 3.11 and install the tested versions in `requirements.txt`. No database or app secrets are required.
4. Deploy and inspect the build/startup logs. Record the actual public URL only after it opens successfully.
5. In a fresh browser session, follow `data/recruiter_demo/README.md`: upload both CSVs, review source previews, match the two order headers, drop Internal Note, and export.
6. Open both downloaded formats and verify five records, four columns, and quantity total 455.
7. Verify duplicate uploads block export, Back/Undo work, a multi-sheet workbook can be selected, and the layout is usable on desktop and mobile.
8. Add the verified live link and real screenshots to the README. Do not describe deployment as complete before these checks pass.

## Practical limits

Uploads are processed in memory. The current user-requested policy has no practical file-size or record-count cap; hosting resources remain finite. Local correctness tests do not establish hosted capacity. Use the small synthetic dataset for the public demonstration. File count remains limited to ten. Excel exports must fit one worksheet; CSV handles outputs beyond Excel's row limit, subject to available memory.

The exact public instance, account access, deployment settings, and browser/download behavior still require verification at publishing time.
