# Published Markdown-memory benchmark snapshot — 2026-09-23

This is the commit-safe snapshot of the final valid full runs for the second memory-system retrieval bakeoff.

Included:

- ai-memory 2.4.0 full 180-case run (`20260923T154221737333Z`);
- agent-memory commit `70d85e5c22081d9dac88c5e908c88ea0bf13af88` full 180-case run (`20260923T155141275179Z`);
- aggregate comparison and backend reports/manifests;
- compact A+D failure records;
- SHA-256 identifiers for the raw `trials.jsonl` files.

EverOS 1.3.1 is **not** included as a scored full-run backend. Its integration reached successful ingestion and Northstar keyword retrieval, but Tell Aster keyword probes returned zero provider hits. The experiment therefore treats EverOS as an incomplete diagnostic integration rather than assigning it a comparable benchmark score.

See `../../../../../docs/markdown-memory-systems-evaluation-2026-09-23.md` for the cross-experiment interpretation and direction.
