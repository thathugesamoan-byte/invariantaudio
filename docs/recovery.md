# Crash Recovery & State Reconciliation

## Software Interruption Recovery
If execution is interrupted (e.g. supervisor process crash or SIGKILL termination):
1. **Pre-Swap Interruption**: Staging files are purged; pre-move backup remains intact.
2. **Post-Swap / Pre-Commit Interruption**: Recovery scanner detects target file matching proposed hash and reconciles SQLite database without re-mutating audio.

*Note: Software crash recovery has been verified against process termination. Physical power-loss durability depends on underlying OS filesystem mount flags and storage write-barrier semantics.*
