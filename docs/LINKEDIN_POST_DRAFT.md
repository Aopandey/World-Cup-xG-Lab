# LinkedIn Post Draft

I built World Cup xG Lab, a full-stack football analytics dashboard for exploring historical chance creation and player context for confirmed 2026 World Cup squads.

The project started as a StatsBomb expected goals model trained on historical shot-location data. As I worked through the squad coverage, I found that many players had limited or missing historical open-data samples. Instead of hiding that limitation, I turned it into a core product feature: the dashboard shows where the model evidence is strong, where it is limited, and where recent club context from FBref, Understat, and DataMB can help fans interpret a player profile more honestly.

Tech stack:

- Python, pandas, scikit-learn, XGBoost
- FastAPI backend
- Next.js + Tailwind frontend
- Docker Compose
- AWS EC2 deployment
- StatsBomb, FBref, Understat, and DataMB context layers

This is not a model that claims to predict exactly who will score at the 2026 World Cup. It is a source-aware scouting dashboard that makes football analytics more visual, honest, and accessible.

The biggest lesson: model quality matters, but data coverage transparency matters just as much.
