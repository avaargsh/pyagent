"""Skill loading helpers."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_skills(root_path: Path) -> dict[str, dict]:
    skill_dir = root_path / "configs" / "skills"
    loaded: dict[str, dict] = {}
    if not skill_dir.exists():
        return loaded
    for path in sorted(skill_dir.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        skill = payload.get("skill", {})
        skill_id = skill.get("id", path.stem)
        loaded[skill_id] = skill
    return loaded
