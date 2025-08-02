# .junie/tasks.md - Project Tasks

> Iteratively implement improvements based on this checklist. After completing each task, mark it with [x] and move to completed.
SHORT TERM TASKS

- [ ] Status-Based Filtering for Quotes**
   - The API supports quote status updates via the `/quotes/public/{quoteNumber}/status_change` endpoint
   - This aligns with your existing task to "Add status-based filtering (`--status-filter`) to quote pulls"
   - Implementation should include filtering by "draft", "outstanding", "cancelled", "lost", and "trash" statuses
- [ ] Integrate all pullers into a unified CLI runner (`run_pull.py`)
- [ ] Build interactive range selection UI (last N, start–stop, all)
- [ ] Write unit and integration tests for each puller and pipeline stage
- [ ] Buyer Integration - Match buyers from Paperless to SOs in Made2Manage
- [ ] Test Updating Quotes - Verify quote updates via the Paperless API
- [ ] Test Assembly Quotes - Analyze component data in Paperless API
   - Verify component visibility, available data, and integration with historical part checker

LONG TERM TASKS
- [ ] Search Functionality**
   - Multiple endpoints support search parameters that could be leveraged in your data pulls
   - For example, accounts can be searched by name, ERP code, notes, and ID
- [ ] ERP Code Integration**
   - Both quotes and orders support updating ERP codes via PATCH operations
   - Consider adding ERP code tracking in your data pipeline to maintain cross-system references
   - This would enable better integration with external ERP systems
- [ ] Refactor pullers to use a common base class for shared functionality
- [ ] Implement a caching layer for pullers to avoid redundant API calls
- [ ] Add support for parallel processing of pullers to speed up data retrieval
- [ ] Purchased components API - track inventory, compare costs, match with INMAST from made2manage
- [ ] Implement a data validation pipeline to ensure data integrity across all pullers
- [ ] Custom Tables Management - The API provides endpoints for managing custom tables used for pricing - can pull and update these tables
- [ ] Extend Pipeline Framework**
   - Add new pipeline types for purchased components and custom tables
   - Implement the `OrderItemPipeline.create_extraction_pipeline` to extract order items
- [ ] Enhance Data Models**
   - Update your data models to include new fields from the API documentation
   - Add support for nested entities like addresses, facilities, and billing addresses
- [ ] Update Documentation**
   - Document the new endpoints and data structures in your project documentation
   - Update examples to show how to use the new features
- [ ] Enhance error handling with specific error types for different API error conditions
- [ ] Implement retry logic with exponential backoff for transient errors
- [ ] Add new CLI options for specifying which related entities to include in data pulls
- [ ] Extend your interactive CLI to support the new data types and filtering options
- [ ] Implement a unified logging framework for all pullers to standardize log output
- [ ] Add support for configurable logging levels per puller
- [ ] Implement a monitoring dashboard to visualize puller performance and data quality metrics

REPEATING TASKS
- [ ] continuously review and update the API documentation for any changes or new features
- [ ] periodically review and refactor the codebase to improve maintainability and performance
- [ ] continuously update README.md with new features, usage examples, and troubleshooting tips
- [ ] periodically review and update the `.junie/guidelines.md` to ensure coding standards are met
- [ ] continuously monitor the API for any changes that may affect your data pipelines
- [ ] periodically review and update the unit tests to ensure they cover new features and edge cases
- [ ] continuously review and update the integration tests to ensure they cover all puller interactions
- [ ] Inconsistent Error Handling 
   - The API documentation shows different error response formats across endpoints
   - Your error handling should be robust enough to handle these inconsistencies
- [ ] Nullable Fields Handling**
   - Many fields are marked as nullable in the API but may be required in certain contexts
   - Your validators should account for these conditional requirements
- [ ] Address Structure Variations**
   - Address structures appear in multiple contexts (contact, account, facility, billing)
   - Consider creating a common address validator/transformer to ensure consistent handling
- [ ] ERP Code Length Limitations**
   - The API specifies a maximum length of 50 characters for some ERP codes
   - Ensure your data validation enforces these constraints
- [ ] Pagination Implementation**
   - The documentation doesn't clearly specify default page sizes for all endpoints
   - Your acquisition stages should handle this gracefully, potentially with configurable defaults

COMPLETED TASKS
- [x] Implement debug mode with verbose logging per module
- [x] Consolidate raw and transformed CSV paths into `data_raw/` and `data_real/`
- [x] Automate S3 upload optionally per loader
- [x] Document style guidelines in `.junie/guidelines.md`
- [x] Filter revised quotes by the requested range in `QuotesPuller.get_all_revisions` (docs/code)
