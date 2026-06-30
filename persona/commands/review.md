---
description: Review a document (file or folder) from the perspective of hostile external personas; produces per-persona feedback + a synthesized report.
argument-hint: <path-to-file-or-folder>
---

A path argument is REQUIRED: `$ARGUMENTS`.

If `$ARGUMENTS` is empty, stop and ask the user for a file or folder path — do not guess or pick
a default.

Otherwise, invoke the `persona-review` skill and run its full pipeline against the given path,
following every phase in order. Treat the personas as external, non-allied reviewers throughout.
