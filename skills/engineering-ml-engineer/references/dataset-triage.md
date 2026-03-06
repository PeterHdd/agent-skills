# Dataset Triage

Use this before choosing a model or launch plan.

## Questions To Answer First

- What is the unit of prediction: row, document, session, image, conversation?
- Who created the labels and how noisy are they?
- Does the dataset include future information or proxy labels that would leak the target?
- What is the real production distribution: balanced, long-tail, time-based drift, or user-segment skew?

## Leakage Checks

- Duplicate rows across train/test.
- IDs or timestamps that encode the answer.
- Features generated after the prediction moment.
- Human-annotated fields that summarize the target.

## Split Selection

- Stratified split for imbalanced classification.
- Time split for anything with sequence, timeline, or user-history effects.
- Group split when examples from one entity must not leak across train/test.
