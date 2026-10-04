# Identification & Candidate Scoring Engine

## Multi-Vector Scoring Formula
$$S(C) = 0.40 \cdot S_{\text{acoust}} + 0.30 \cdot S_{\text{title}} + 0.20 \cdot S_{\text{artist}} + 0.10 \cdot S_{\text{album}}$$

## Strict Decision Gates
- **Duration Gate**: Candidate duration must match decoded audio duration within $\pm 3.0\text{s}$.
- **Acoustic Margin Gate**: Top candidate must achieve $S_1 \ge 0.80$, runner-up $S_2 \le 0.20$, margin $\Delta S \ge 0.60$, and overlap $\ge 150$ frames.
- **Live-Veto Authority**: Dynamic database check blocking covers, live recordings matching studio cuts, and unconfirmed remixes.
