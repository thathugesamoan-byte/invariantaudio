# Stream Health Classification

`inspect_stream_health` (CLI: `verify`) runs `ffmpeg -v warning -i FILE -f null -` and classifies the result from the exit code and the text of its warnings:

| Status | Rule |
|---|---|
| `UNUSABLE` | `ffmpeg` exits non-zero |
| `TRUSTED` | exit 0 and no output on stderr |
| `INTEGRITY_EXCEPTION` | stderr contains `bit reservoir underflow` or `sync error` **and** (`partial file` or `Invalid data found`) |
| `DAMAGED_BUT_PLAYABLE` | any other non-empty stderr |

Limits: this is string-matching on `ffmpeg` output. It is a triage aid, not a forensic analysis, and its wording depends on the `ffmpeg` version. The engine records the status of the source; it does not repair audio (no clipping, no re-encoding). The `quarantine` function moves a file out of the library tree with a backup; it is not triggered automatically by any status.
