# Archived Scripts

This directory contains scripts that were previously used in the project but are no longer needed. They have been archived for reference purposes.

## List of Archived Scripts

1. **process_contacts_fixed_ranges.py** - A script for processing contacts in fixed ID ranges to avoid timeouts. This was a temporary solution before implementing proper pagination in the contacts puller.

2. **process_contacts_in_chunks.py** - A script for processing contacts in chunks to avoid timeouts. This was a temporary solution before implementing proper pagination in the contacts puller.

3. **process_single_contact_range.py** - A script for processing a subset of contacts from a list of contact IDs. This was a temporary solution before implementing proper pagination in the contacts puller.

4. **test_contacts_puller.py** - A script for testing the ContactsPuller directly to debug pagination issues. This was used during development and is no longer needed.

5. **testing.py** - A general testing script that was used during development and is no longer needed.

6. **dump_one_quote_order.py** - A utility script for fetching and saving a specific quote and order from the API. It contained hardcoded API keys and IDs, which is a security risk.

## Current Solution

The current solution for fetching contacts is implemented in `scripts/pull_contacts.py`, which correctly handles pagination and has been tested to successfully fetch all contacts without timing out.

The pipeline has been updated to use this new script through the `NewContactsDataAcquisitionStage` class in `scripts/pipeline/account_contact_processors.py`.