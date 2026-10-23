# Recruiter demonstration data

These two CSV files are entirely synthetic. Supplier names, identifiers, quantities, and notes are invented for this project and contain no employer or customer information. They were authored for this project, not downloaded from Olist or another dataset.

## Two-minute workflow

1. Download `01_warehouse_north.csv` and `02_warehouse_south.csv` from this folder, then upload both to the app. No data loads automatically.
2. Confirm **2 files / 2 datasets / 5 input rows / 5 output rows**.
3. Click **Next: Review data**. Expand a source preview, then inspect the output below it. Initially there are six columns because Order Number and Purchase Order have different names.
4. Expand **Match or drop columns**. Select **Order Number** and **Purchase Order**, retain **Order Number**, and click **Treat as the same column**.
5. Select **Internal Note** under Columns to drop and click **Drop column**.
6. The output now has five records and four columns: Order Number, Supplier, Part Number, Quantity. Quantity totals 455; no records are excluded.
7. Click **Next: Export** and download Excel or CSV. Open it to verify five rows and the four expected columns. Back/Undo can restore prior column choices.

The generated expected master CSV is in `docs/examples/recruiter-master.csv`. It is verified against the processing engine by an automated test.
