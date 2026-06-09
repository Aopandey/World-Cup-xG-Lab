# Portfolio Case Study

## Problem

Football fans want to understand which players and teams create high-quality chances, but xG dashboards can be either too technical or too confident about uncertain data.

World Cup data is especially difficult because squads include players from many leagues, and open event-data coverage is uneven.

## Why I Built It

I wanted to build a project that combines machine learning, data engineering, product design, and deployment in one football analytics product.

The goal was not to predict exactly who will score. The goal was to make historical chance quality and data limitations easy to explore.

## Data Challenge

The first version used StatsBomb Open Data for shot-level xG modeling. That worked well for teams and players represented in open competitions, but many 2026 World Cup squad players had weak or missing shot samples.

That led to a broader source-aware product design:

- Keep StatsBomb as the production model layer.
- Add FBref as recent aggregate form context.
- Add Understat as club xG context.
- Add DataMB as percentile scouting context.
- Show weak-sample warnings instead of hiding uncertainty.

## Model Approach

The production model is an XGBoost classifier trained on StatsBomb shot data.

It uses location, geometry, body part, shot type, pressure, play pattern, minute, and period to estimate goal probability.

The model is evaluated with log loss, Brier score, ROC-AUC, and accuracy. Log loss and Brier score are emphasized because xG is a probability-calibration problem.

## Product/Dashboard Approach

The dashboard is built around football-native questions:

- What do we know about this team?
- Which players have useful historical shot evidence?
- Where is the data strong or weak?
- What recent club context helps when historical samples are limited?

The UI separates source layers so users can understand whether a number comes from the model, recent club form, or an external percentile profile.

## Data-Source Evolution

1. StatsBomb first for shot-level xG modeling.
2. Discovered coverage limits for some 2026 World Cup players.
3. Added FBref for recent aggregate player context.
4. Added Understat for club xG context and model experiments.
5. Added DataMB for 25/26 percentile profiles.
6. Separated model output from context layers to avoid overclaiming.

## Technical Architecture

- Python ingestion, validation, and feature engineering scripts.
- scikit-learn and XGBoost model training.
- MLflow experiment tracking.
- JSON artifact generation for dashboard consumption.
- FastAPI backend serving precomputed artifacts.
- Next.js + Tailwind frontend.
- Docker Compose deployment on AWS EC2.

## What I Learned

- A useful analytics product is not just a model; it is also coverage transparency.
- Accuracy can be misleading for xG because most shots are not goals.
- Source boundaries matter when combining event data, aggregate stats, and external model outputs.
- Weak samples should be designed for directly instead of treated as an edge case.

## Future Work

- Add HTTPS and a production domain.
- Expand source-model comparison.
- Improve calibration plots and model diagnostics.
- Improve shot-map interactivity.
- Add licensed player images or approved placeholders.
- Add CI/CD checks for build, validation, and deployment.
