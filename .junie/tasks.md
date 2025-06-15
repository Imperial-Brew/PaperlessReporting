# Project Tasks

> Iteratively implement improvements based on this checklist. After completing each task, mark it with [x].

- [ ] Filter revised quotes by the requested range in `QuotesPuller.get_all_revisions` (docs/code)
- [ ] Add status-based filtering (`--status-filter`) to quote pulls
- [ ] Integrate all pullers into a unified CLI runner (`run_pull.py`)
- [ ] Build interactive range selection UI (last N, start–stop, all)
- [ ] Implement debug mode with verbose logging per module
- [ ] Consolidate raw and transformed CSV paths into `data_raw/` and `data_real/`
- [ ] Automate S3 upload optionally per loader
- [ ] Document style guidelines in `.junie/guidelines.md`
- [ ] Draft improvement plan in `docs/plan.md`
- [ ] Write unit and integration tests for each puller and pipeline stage