1. Scheduled Pipeline Runs
   - Quotes & Quote Items → hourly
   - Orders & Order Items → 2–3× per day (e.g., 6 am, 2 pm, 10 pm)
   - Accounts, Contacts & Users → daily (e.g., 3 am)

2. Webhook‐Driven Incrementals
   - order.created → pull that one order + its items, append to master CSV
   - quote.sent → pull that quote (and items), update master CSVs
   - quote.created → delay ~1 hr then pull full quote + items (to allow PDFs, attachments)

3. Data Management & Lifecycle
   - Master (“Golden”) CSVs per entity (quotes.csv, quote_items.csv, etc.)—the canonical source for Power BI
   - Raw vs. Cleaned Folders for troubleshooting:
     * data_raw/… (exact API dumps)
     * data_real/… (post-pipeline, but pre-archival)
   - Archival & Retention
     * Rotate out raw/real older than X days
     * Move “historical” masters to a cold bucket


LATER:
4. Further Automation & Integration
   - Auto-email reports (e.g., “New Quotes This Hour” with summary metrics)
   - Enrichment & Scoring (Buyer/Estimator performance dashboards)
   - Internal Sharing (CLI or simple web UI for triggering pulls and viewing status)
   - External Packaging (evaluate productizing the pipeline)


MUCH LATER:
[assign time for each quote-
Data Entry/validation: 
    - Quote Setup - 30 minute minimum
	- each line item 1 minute
Quoting:
	30 mins for 'setup' (reading notes, checking repeats/emails/chats, verify data) 
    - each quote item gets 30 mins +
	10 mins per component in assy
	15 mins for review/COMPLETE
Data entry/validation:
	30 minute (minimum) upload
	    + 1 min/line
--connect these with MOTION.app--]

{Link with future app from Imperial_Brew- Vendor Emailing App}



Wild-hare ideas
	- robust purchased component identification (paperless does this already, but we have more  specific data/history on  which to compare)