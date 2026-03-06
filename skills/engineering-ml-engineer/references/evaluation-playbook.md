# Evaluation Playbook

Use this when the task needs more than "accuracy improved."

## Baselines

- Classification: majority class and TF-IDF + logistic regression for text.
- Regression: mean predictor and a simple tree-based regressor.
- Ranking or retrieval: keyword baseline or BM25 before dense retrieval.
- Generation: exact task-specific rubric plus a small human review set.

## Acceptance Gates

- Beat baseline by a pre-defined margin.
- Show stable results across seeds or folds.
- Demonstrate no critical regression on edge cases.
- Meet deployment latency and cost targets.

## Human Review

- Sample at least 20 predictions from the best run.
- Include both easy and hard examples.
- If humans reject more than 15% of sampled outputs for the core use case, the model is not production-ready.
