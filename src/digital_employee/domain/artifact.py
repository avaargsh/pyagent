"""Artifact model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    name: str
    uri: str
    created_at: str
