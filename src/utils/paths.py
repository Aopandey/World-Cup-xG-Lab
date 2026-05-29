from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    """Return a path inside the project root."""
    return get_project_root().joinpath(*parts)
