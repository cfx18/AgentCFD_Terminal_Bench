# Tutorial Authoring v1

This release contains 49 generated OpenFOAM tutorial-derived benchmark task packages.

Each task directory is copied from a completed authoring worker's `work/package/`
artifact and contains the public task materials produced by the authoring run.
The raw authoring run directories, model transcripts, API receipts, temporary
worker state, and native runtime artifacts are intentionally not included here.

Review status:

- 49 tasks have complete `author-result.json` and `REVIEW.zh.md` source evidence
  in the authoring run manifest.
- The public task descriptions were reviewed separately; see
  `docs/tutorial-authoring-v1/REVIEW_TABLE.zh.md`.
- Description-review summary: 40 pass, 9 review, 0 fail.

Important scope note:

These packages are authoring candidates, not automatically certified scientific
truth. The review table identifies tasks that need human attention before being
used as a final scored benchmark.

