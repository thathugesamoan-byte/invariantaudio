# Third-Party Licenses & Software Notices

InvariantAudio depends on third-party libraries and standalone tools, and plans (but does not yet contain) integrations with external services. This document outlines their licensing and distribution relationships.

---

## 1. Runtime Python Dependencies

### Mutagen
* **Upstream Project**: [Mutagen](https://github.com/quodlibet/mutagen)
* **Relationship**: `PYTHON_RUNTIME_DEPENDENCY` (Dynamically imported library: `import mutagen`).
* **License**: GNU General Public License v2.0 or later (`GPL-2.0-or-later`).
* **Redistribution**: InvariantAudio does NOT bundle or copy Mutagen source code. Mutagen is installed independently as a standard package requirement via `pip`.

### PyYAML
* **Upstream Project**: [PyYAML](https://pyyaml.org/)
* **Relationship**: `PYTHON_RUNTIME_DEPENDENCY` (Dynamically imported library: `import yaml`).
* **License**: MIT License.
* **Redistribution**: Installed independently via `pip`.

---

## 2. External Standalone Executables (System Requirements)

### FFmpeg & ffprobe
* **Upstream Project**: [FFmpeg](https://ffmpeg.org/)
* **Relationship**: `EXTERNAL_EXECUTABLE` (Invoked purely via CLI subprocess: `subprocess.run(["ffmpeg", ...])`).
* **License**: LGPL v2.1+ / GPL v2+ (depending on user compilation flags).
* **Redistribution**: InvariantAudio does NOT bundle, distribute, or compile FFmpeg binaries. Users install FFmpeg through standard operating system package managers.

### Chromaprint / fpcalc
* **Upstream Project**: [Chromaprint](https://acoustid.org/chromaprint)
* **Relationship**: `EXTERNAL_EXECUTABLE` (optional; invoked via CLI subprocess by `discovery.compute_acoustic_fingerprint`, which no command or test calls in v0.1.0-alpha).
* **License**: LGPL v2.1+ / MIT.
* **Redistribution**: InvariantAudio does NOT bundle or distribute `fpcalc` binaries.

---

## 3. Platform Components & Standard Libraries

### SQLite 3
* **Relationship**: `STANDARD_LIBRARY_OR_PLATFORM_COMPONENT` (`import sqlite3`).
* **License**: Public Domain.

---

## 4. External Network Metadata Services

> **Neither service below is contacted by v0.1.0-alpha.** The package contains no network code. These entries describe planned integrations.

### MusicBrainz
* **Relationship**: `PLANNED_EXTERNAL_NETWORK_SERVICE` (not used in this release).
* **Data License**: Core metadata is in the Public Domain (Creative Commons CC0).
* **Note**: InvariantAudio is an independent client and is not endorsed by or affiliated with the MetaBrainz Foundation.

### AcoustID
* **Relationship**: `PLANNED_EXTERNAL_NETWORK_SERVICE` (not used in this release).
* **Note**: fingerprint submission is prohibited by project policy (`enable_acoustid_submission: true` is rejected by the configuration parser).
