"""Heuristic worker selection for coordinated execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from digital_employee.domain.employee_profile import EmployeeProfile

_STOP_WORDS = {
    "about",
    "after",
    "before",
    "draft",
    "follow",
    "please",
    "prepare",
    "pricing",
    "quotes",
    "summary",
    "write",
}


@dataclass(slots=True)
class CoordinatorSelection:
    worker_profile: EmployeeProfile
    reason: str
    required_tools: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)


class CoordinatorSelector:
    def select(
        self,
        *,
        participant_profiles: list[EmployeeProfile],
        prompt: str,
    ) -> CoordinatorSelection:
        required_tools = self._infer_required_tools(prompt)
        prompt_terms = self._extract_terms(prompt)
        best_profile = participant_profiles[0]
        best_score = float("-inf")
        best_reason = "fallback:first-participant"
        best_terms: list[str] = []

        for profile in participant_profiles:
            score, reason, matched_terms = self._score_profile(
                profile=profile,
                required_tools=required_tools,
                prompt_terms=prompt_terms,
            )
            if score > best_score:
                best_profile = profile
                best_score = score
                best_reason = reason
                best_terms = matched_terms

        return CoordinatorSelection(
            worker_profile=best_profile,
            reason=best_reason,
            required_tools=required_tools,
            matched_terms=best_terms,
        )

    def _score_profile(
        self,
        *,
        profile: EmployeeProfile,
        required_tools: list[str],
        prompt_terms: list[str],
    ) -> tuple[int, str, list[str]]:
        score = 0
        reasons: list[str] = []
        matched_tools = [tool for tool in required_tools if tool in profile.allowed_tools]
        if matched_tools:
            score += 10 * len(matched_tools)
            reasons.append(f"tool-match:{','.join(matched_tools)}")
            if len(matched_tools) == len(required_tools) and required_tools:
                specialization_bonus = max(0, 3 - len(profile.allowed_tools))
                if specialization_bonus:
                    score += specialization_bonus
                    reasons.append("specialist-bias")
        elif required_tools:
            score -= 5 * len(required_tools)

        corpus = " ".join(
            [
                profile.employee_id,
                profile.display_name,
                *profile.skill_packs,
                *profile.knowledge_scopes,
            ]
        ).lower().replace("-", " ")
        matched_terms = [term for term in prompt_terms if term in corpus]
        if matched_terms:
            deduped_terms = sorted(set(matched_terms))
            score += 2 * len(deduped_terms)
            reasons.append(f"term-match:{','.join(deduped_terms[:3])}")
            matched_terms = deduped_terms

        if score <= 0:
            return score, "fallback:first-participant", matched_terms
        return score, "+".join(reasons), matched_terms

    def _infer_required_tools(self, prompt: str) -> list[str]:
        prompt_lower = prompt.lower()
        required_tools: list[str] = []
        if any(marker in prompt_lower for marker in ("email", "outreach", "reply")) or re.search(
            r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
            prompt_lower,
        ):
            required_tools.append("send-email")
        if any(marker in prompt_lower for marker in ("research", "search", "find", "lookup", "knowledge", "playbook")):
            required_tools.append("knowledge-search")
        return required_tools

    def _extract_terms(self, prompt: str) -> list[str]:
        terms: list[str] = []
        for item in re.findall(r"[a-z0-9-]{4,}", prompt.lower()):
            if item not in _STOP_WORDS:
                terms.append(item.replace("-", " "))
        return terms
