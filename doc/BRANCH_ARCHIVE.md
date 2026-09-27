# Branch archive

At Tianyi's request, `main` became the integrated working branch, and the five
other branches were archived and deleted on 2026-09-26. Tags were pushed and
verified before branch deletion. No firmware code changed during this cleanup.

| Deleted branch | Archive tag | Saved commit |
| --- | --- | --- |
| lab2-integration | archive-lab2-integration-2026-09-26 | 18da014 |
| lab2-tianyi | archive-lab2-tianyi-2026-09-26 | 4adfe33 |
| lab2-tianyi-blinkers | archive-lab2-tianyi-blinkers-2026-09-26 | 7745808 |
| lab2-tianyi-steering | archive-lab2-tianyi-steering-2026-09-26 | 1d11ef2 |
| part3_starter | archive-part3-starter-2026-09-26 | d0870a0 |

All four `lab2-*` tips are ancestors of the integrated main. `part3_starter`
contains four commits outside main; its tag preserves those commits without
merging its old starter implementation into the working firmware.

The separate tag `main-before-lab2-integration-2026-09-26` preserves main's
previous motor/PID tip, `983cb1b`.

## Recover an archived version

A tag saves the commit and its history. To work from an old version, create a
new branch from the relevant tag; this leaves main intact. For example:

```bash
git fetch origin --tags
git switch -c recovered-part3 archive-part3-starter-2026-09-26
```

Replace the tag with any entry above to recover that version. This creates a
separate working branch; it does not roll main back or overwrite teammates'
later changes.
