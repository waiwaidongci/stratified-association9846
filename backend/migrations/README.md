# Initial schema
SQLAlchemy metadata.create_all initializes the business tables plus users and audit on first start. Unique keys: study.code, (stratum.study_id,stratum.code), count.stratum_id, run.name, note.title. Foreign keys form study→stratum→count and study→run→note. This is not a production schema migration mechanism; use a versioned migration tool before evolving persisted deployments.

## Paired re-test extension (paired_* tables)
The whole-piece label-swap paired study adds six tables, all created by the same metadata.create_all (no data migration of the existing four-fold tables, whose results are unchanged):

- paired_studies (unique code): one paired re-test investigation.
- paired_layers (unique study_id+code): the 2..8 pre-declared humidity layers, with a stable sequence.
- paired_pieces (unique study_id+code): the 1..60 re-tested pieces, with per-piece source.
- paired_cells (unique piece_id+layer_id): the frozen 0/1 success/failure of both package types for one piece on one layer; this is the smallest unit that keeps the within-piece cross-layer association.
- paired_runs (unique name): queued/running/completed/failed paired computation, holding the immutable input_snapshot JSON, result JSON (tail/interior/total combination counts as decimal strings) and error text.
- paired_verification_notes (unique title): draft/approved/rejected independent re-test notes; only approved notes can be exported.

Foreign keys: paired_study→paired_layer/paired_piece→paired_cell, paired_study→paired_run→paired_verification_note. Existing association_* tables and their method version (cmh-mean-distance-exact-v1) are untouched.
