# Audio import feedback and recovery

The previous browser waited on a single synchronous transcription request after
uploading. Only the small global status line distinguished upload from inference,
and inference held the workspace lock, delaying library/report requests.

Imports now show a persistent panel below **Import vocal audio**:

- Upload transfer progress (measured bytes, not an estimated inference percentage).
- File-received confirmation, queued status and processing elapsed time.
- Ready confirmation and **Open song**, with an automatic library update.
- Specific processing errors and **Retry processing**, using the existing upload.

The browser polls `/api/import-jobs`; `/api/import-start` returns immediately.
One background worker processes queued recordings through the existing analysis
pipeline without holding the workspace UI lock. Identical requests already queued,
processing or complete reuse their job. Status is atomically persisted under
`outputs/import-jobs`. Reloading the browser recovers progress; restarting the
server marks unfinished jobs interrupted and offers a retry. Restart does not
silently rerun inference. Uploads remain under `outputs/imports`.

Completion opens the song if the user has stayed on the same recording and has no
unsaved corrections/composition. Otherwise the ready panel offers an explicit open
action. Existing predictions, annotations and revision formats are unchanged.

CPU inference can still take minutes for longer files. Processing has an
indeterminate progress bar because the pipeline does not report a trustworthy
completion percentage. An in-flight file transfer cannot survive a page reload;
once the server has accepted the processing job, tracking does survive reload.

Validation commands:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
npm run test:editor
npm run test:browser
```

New coverage includes real WAV transfer and pretrained-free pYIN processing on a
disposable synthetic recording, automatic readiness/library refresh, reload
recovery, protection of unsaved edits, exact failure feedback, retry without
re-upload, job deduplication, serial queue execution, restart recovery and an
available workspace lock while inference is blocked. Controlled status responses
are used specifically to test slow/failing UI states; those are not model results.

Verified 2026-11-05: 91 Python tests, 11 JavaScript editing tests and all 90
browser tests passed. Browser coverage ran at 1366×768 and 1920×1080 using
disposable fixtures. No user audio, reference revisions or saved ideas were used
as upload test targets.
