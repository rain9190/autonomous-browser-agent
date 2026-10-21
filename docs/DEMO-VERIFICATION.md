# Local demo verification — 22 October 2026

Observed from user-supplied screenshots and terminal output in the project conversation.
Demo implementation commit: `332f646`. Final evidence/report commit: `aba1584`.
Protocol commit: `317eba5`. No additional browser runs or API requests were made to write
this record. The following five calls are live-development demo calls, separate from the
201 reported final-evaluation calls; they are not a total for all project development.

| Check | Task / development seed | Outcome | Calls | Action attempts | Recoveries | Worker exit |
|---|---|---|---:|---:|---:|---:|
| Basic live interface | enter-text / 61 | Full credit | 2 | 2 | 0 | 0 |
| Controlled recovery interface | enter-text / 61 | Full credit | 3 | 3 | 1 | 0 |

The basic trace showed observe → decide → validate → execute → verify twice, filling
observed field 14 and clicking button 15. The recovery trace showed an induced first-fill
failure, a fresh decision and successful fill, then submission. This establishes the tested
interface paths; it does not establish spontaneous-error recovery or arbitrary website support.

The recorded overview loaded 55/60 one-shot, 57/60 iterative and 6/6 controlled recovery on.
The displayed episode counts and summary values match the audited evidence. The expanded
row table and filter were not shown in these screenshots.

User-installed tests: 268 passed, 10 optional browser checks skipped. The user subsequently
ran the frozen protocol checker successfully with zero browser launches and API calls.
The final log showed `332f646`, `aba1584`, `317eba5` in order, and git status listed only
untracked historical README files, day2.gitignore and vendor/. No tracked modifications
were reported at that checkpoint.

Active Stop cancellation, live concurrent-run prevention, restart behavior and clean-machine
installation have not been manually established by this evidence. Successful worker exit and
return to terminal do not prove every cancellation path. Raw model responses, filled values
and credentials are not included in this record. Original screenshots remain in the project
conversation; this bundle adds a written observation record, not new benchmark episode JSON.
