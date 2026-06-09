# Model Card

## Model Objective

Estimate the probability that a football shot becomes a goal using historical shot-level data.

The model output is expected goals, or xG. A 0.10 xG shot means similar shots are expected to be scored about 10% of the time.

## Target

`is_goal`

Binary target:

- `1`: shot resulted in a goal.
- `0`: shot did not result in a goal.

## Training Data

The production model is trained on historical StatsBomb Open Data shot events.

The enriched shot data includes match metadata where available, including competition, season, match date, home team, and away team.

## Features

Production features include:

- `shot_x`
- `shot_y`
- `distance_to_goal`
- `angle_to_goal`
- `body_part`
- `shot_type`
- `under_pressure`
- `play_pattern`
- `minute`
- `period`

Categorical features are one-hot encoded. Numeric features are passed through model preprocessing.

## Model

Production model:

- XGBoost classifier.

Baseline:

- Logistic regression with scikit-learn preprocessing.

## Metrics

| Model | Log Loss | Brier Score | ROC-AUC | Accuracy at 0.5 |
|---|---:|---:|---:|---:|
| XGBoost xG model | 0.283 | 0.081 | 0.795 | 0.899 |
| Logistic regression baseline | 0.286 | 0.082 | 0.789 | 0.899 |

Log loss and Brier score are prioritized because xG is a probability problem. Accuracy is shown only as a secondary metric because most shots are not goals.

## Intended Use

- Explore historical shot quality for players and teams.
- Compare chance quality across available historical samples.
- Support a fan-friendly scouting dashboard.
- Show where evidence is strong, limited, or missing.

## Non-Intended Use

- Betting decisions.
- Guaranteed 2026 World Cup predictions.
- Claims that a player will score from a specific location.
- Directly ranking player ability without context.

## Data Leakage Considerations

The production model does not use another source's published xG as an input feature.

Understat's published xG is kept as `source_xg` for benchmarking only. It is not used as a model input because that would leak another model's answer into our model.

## Limitations

- StatsBomb Open Data coverage is uneven across countries and years.
- Some 2026 World Cup teams have no historical StatsBomb sample in the current artifact set.
- Small shot samples are noisy.
- Club context and international context are separate and should not be blended without explanation.
- Player/source matching can miss players when names differ across datasets.

## Future Comparison Plan

Future experiments should compare:

- StatsBomb-only model.
- Understat-only model.
- Combined-source model.
- Feature-missingness scenarios where some source features are unavailable.

These experiments should report log loss, Brier score, ROC-AUC, calibration plots, and coverage differences.
