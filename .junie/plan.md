# Project Improvement Plan

## Phase 1: Immediate Fixes
1. Filter revisions by range / status in QuotesPuller (`3 days`)
2. Surface CSVLoader logs for visibility (`1 day`)
3. Clean up context propagation for quote items (`1 day`)

## Phase 2: Unified CLI Runner
- Design `run_pull.py` interactive flow (`2 days`)
- Integrate all existing pullers under one command
- Support range, status, output path, debug flags

## Phase 3: Testing & CI
- Write pytest suites for pullers & pipeline stages
- Add GitHub Actions workflow to run smoke tests on new PRs

## Phase 4: Documentation & Handoff
- Finalize `.junie/guidelines.md` and `docs/tasks.md`
- Create architecture diagram
- Prepare handoff notes for Junie and other team members