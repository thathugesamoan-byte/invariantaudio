# Identification & Candidate Scoring (partial in v0.1.0-alpha)

**Status: building blocks only.** There is no MusicBrainz or AcoustID client, no fingerprint-to-candidate pipeline, and no command that scores real candidates. The functions below exist, are unit-tested, and are not called by any workflow.

## Implemented functions (`invariantaudio.evidence`, `.duplicates`, `.identification`, `.discovery`)
- `calculate_composite_score(acoustic, title, artist, album_match)` = `0.40·acoustic + 0.30·title + 0.20·artist + 0.10·album`.
- `passes_duration_gate(file_dur, cand_dur, tolerance=3.0)`.
- `evaluate_auto_approval_eligibility(top, runner_up, overlap_frames, file_dur, cand_dur)`: requires duration difference ≤ **2.0 s**, overlap ≥ 150 frames, top ≥ 0.80, runner-up ≤ 0.20, margin ≥ 0.60. (The 3.0 s default of `passes_duration_gate` is looser than this function's fixed 2.0 s.) Thresholds are module constants; the `scoring:` configuration block is validated but not consumed.
- `check_version_veto(source_title, candidate_title)`: a case-insensitive **substring** comparison of the keywords `live, remix, tribute, cover, acoustic, karaoke, instrumental`; returns True if exactly one of the two titles contains a keyword. It consults no database and is deliberately conservative (e.g. "alive" contains "live").
- `sanitize_search_query(text)`: removes bracketed text and a leading track number. Not a privacy filter.
- `compute_acoustic_fingerprint(path)`: runs `fpcalc -json`; requires Chromaprint's `fpcalc` on `PATH`.

## Planned
Fingerprint lookup, candidate retrieval and ranking against MusicBrainz, and the approval flow that would consume these gates ([approval-model.md](approval-model.md)).
