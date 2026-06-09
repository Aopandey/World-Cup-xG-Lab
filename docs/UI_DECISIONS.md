# UI Decisions

World Cup xG Lab is designed to be understandable for normal football fans while still showing technical depth.

## Product Principle

Default view:

```text
Fan-friendly scouting story
```

Advanced view:

```text
Proof that the data and model pipeline are serious
```

## Language Choices

The dashboard avoids language that sounds like guaranteed predictions.

Preferred labels:

- Past sample shots.
- Past sample xG.
- Historical model xG.
- Average chance quality.
- Finishing vs expected.
- Strong evidence, some evidence, limited evidence, no historical sample.

Avoided labels:

- Predicted goals.
- Best team.
- Guaranteed scorer.
- Will score from here.

## Source Separation

The UI keeps sources visibly separate:

- StatsBomb: historical model and shot-location layer.
- FBref: recent aggregate player context.
- Understat: club xG context.
- DataMB: percentile profile context.

This prevents users from thinking all numbers come from the same model.

## Weak Sample UX

Weak samples are treated as a normal user journey, not an edge case.

When historical StatsBomb shots are limited, the UI shifts attention toward source availability, club context, and coverage explanations instead of showing empty model-heavy sections.

## Squad Board

The Squad Board is intentionally called a Data XI, not a predicted lineup.

It shows players with the strongest available data profile in a football-shaped layout. It does not claim to be the real starting XI.

## Empty States

No-data states explain what happened:

- The source may not cover the league.
- The player may not appear in open StatsBomb competitions.
- Name matching may not be reliable enough.

The UI avoids treating missing data as a player-quality judgment.
