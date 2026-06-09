# Project Summary

World Cup xG Lab is a portfolio-ready football analytics dashboard for exploring historical chance creation and finishing context for confirmed 2026 World Cup teams and players.

The project combines a StatsBomb-trained expected goals model with source-aware context layers from FBref, Understat, and DataMB. It is designed for football fans who want useful scouting context without being misled into thinking limited open data can precisely predict future World Cup scoring.

## Goal

The goal is to make xG and data coverage easy to understand:

- What historical shot evidence exists for a team or player?
- Which players generated high-quality chances in available data?
- Where is the model evidence strong, limited, or missing?
- What recent club context can still help when historical international samples are weak?

## Product Positioning

This is a scouting and analytics dashboard, not a guaranteed tournament prediction model.

The default experience is fan-friendly. The advanced pages preserve model metrics, source coverage, and technical proof for recruiters or technical reviewers.

## Production Architecture

- Next.js + Tailwind frontend.
- FastAPI backend.
- Precomputed JSON artifacts in `data/dashboard_artifacts/`.
- Docker Compose deployment.
- Nginx reverse proxy on EC2.
- Streamlit retained only as an early prototype.

## Current Data Layers

- StatsBomb: historical shot-location xG model and shot maps.
- FBref: recent aggregate player form context.
- Understat: club xG context and experimental source-model research.
- DataMB: 25/26 percentile scouting profiles where available.
