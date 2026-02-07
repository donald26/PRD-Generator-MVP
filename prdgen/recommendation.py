"""
Intelligent artifact recommendation system.

Analyzes the document context summary to recommend which artifacts should be generated,
with confidence scores and rationale.
"""
import json
import logging
from typing import Dict, List, Set, Any
from pathlib import Path
from dataclasses import dataclass, asdict

from .artifact_types import ArtifactType

LOG = logging.getLogger("prdgen.recommendation")


@dataclass
class ArtifactRecommendation:
    """Recommendation for a specific artifact type"""
    artifact_type: str
    confidence: int  # 0-100
    rationale: str
    recommended: bool


class RecommendationEngine:
    """
    Analyzes document context to recommend appropriate artifacts for generation.

    The engine examines the context summary structure and content to determine:
    - Which artifacts are strongly recommended (confidence >= 80)
    - Which are moderately recommended (confidence 50-79)
    - Which are not recommended (confidence < 50)
    """

    # Confidence thresholds
    CONFIDENCE_HIGH = 80
    CONFIDENCE_MEDIUM = 50

    def __init__(self):
        self.recommendations: List[ArtifactRecommendation] = []

    def analyze_context(self, context_summary: str) -> List[ArtifactRecommendation]:
        """
        Analyze context summary and generate recommendations.

        Args:
            context_summary: The generated context summary markdown

        Returns:
            List of artifact recommendations with confidence scores
        """
        LOG.info("Analyzing context summary for artifact recommendations")

        # Parse context summary to extract key signals
        signals = self._extract_signals(context_summary)

        # Generate recommendations for each artifact type
        recommendations = []

        # PRD - Always highly recommended as it's the foundation
        recommendations.append(self._recommend_prd(signals))

        # Capabilities - Recommended if functional requirements are detailed
        recommendations.append(self._recommend_capabilities(signals))

        # Capability Cards - Recommended if capabilities are complex
        recommendations.append(self._recommend_capability_cards(signals))

        # Epics - Recommended if scope is large or has multiple themes
        recommendations.append(self._recommend_epics(signals))

        # Features - Recommended if epics are recommended and requirements are detailed
        recommendations.append(self._recommend_features(signals))

        # User Stories - Recommended for development-ready projects
        recommendations.append(self._recommend_user_stories(signals))

        # Lean Canvas - Recommended for business/strategic planning
        recommendations.append(self._recommend_lean_canvas(signals))

        # Technical Architecture - Recommended when technical complexity is indicated
        recommendations.append(self._recommend_technical_architecture(signals))

        self.recommendations = recommendations
        LOG.info(f"Generated {len(recommendations)} artifact recommendations")

        return recommendations

    def _extract_signals(self, context_summary: str) -> Dict[str, Any]:
        """
        Extract key signals from context summary.

        Signals help determine which artifacts are appropriate:
        - Problem clarity: How well-defined is the problem?
        - Goal specificity: Are goals concrete and measurable?
        - Requirement detail: How detailed are the requirements?
        - Persona definition: Are users well-defined?
        - Technical complexity: Is this technically complex?
        - Business focus: Is this business/strategy focused?
        """
        signals = {
            "has_problem": "## Problem / Opportunity" in context_summary and "Not specified" not in context_summary.split("## Problem / Opportunity")[1].split("##")[0],
            "has_goals": "## Goals" in context_summary and "Not specified" not in context_summary.split("## Goals")[1].split("##")[0] if "## Goals" in context_summary else False,
            "has_personas": "## Target Personas" in context_summary and "Not specified" not in context_summary.split("## Target Personas")[1].split("##")[0] if "## Target Personas" in context_summary else False,
            "has_requirements": "## Key Functional Requirements" in context_summary and "Not specified" not in context_summary.split("## Key Functional Requirements")[1].split("##")[0] if "## Key Functional Requirements" in context_summary else False,
            "has_constraints": "## Constraints & Assumptions" in context_summary and "None specified" not in context_summary.split("## Constraints & Assumptions")[1].split("##")[0] if "## Constraints & Assumptions" in context_summary else False,
        }

        # Count requirements to assess detail level
        if signals["has_requirements"]:
            req_section = context_summary.split("## Key Functional Requirements")[1].split("##")[0]
            signals["requirement_count"] = req_section.count("\n-")
        else:
            signals["requirement_count"] = 0

        # Count goals to assess scope
        if signals["has_goals"]:
            goals_section = context_summary.split("## Goals")[1].split("##")[0]
            signals["goal_count"] = goals_section.count("\n-")
        else:
            signals["goal_count"] = 0

        # Count personas to assess user diversity
        if signals["has_personas"]:
            persona_section = context_summary.split("## Target Personas")[1].split("##")[0]
            signals["persona_count"] = persona_section.count("\n-")
        else:
            signals["persona_count"] = 0

        # Check for business vs technical focus
        lower_text = context_summary.lower()
        business_keywords = ["revenue", "market", "customer", "business", "strategy", "competitive"]
        technical_keywords = ["api", "database", "architecture", "system", "integration", "technical"]

        signals["business_focus"] = sum(1 for kw in business_keywords if kw in lower_text)
        signals["technical_focus"] = sum(1 for kw in technical_keywords if kw in lower_text)

        LOG.debug(f"Extracted signals: {signals}")
        return signals

    def _recommend_prd(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """PRD is almost always recommended as the foundation"""
        if signals["has_problem"] and signals["has_goals"]:
            confidence = 95
            rationale = "Strong foundation: clear problem and goals defined"
        elif signals["has_problem"] or signals["has_goals"]:
            confidence = 85
            rationale = "Basic context available for PRD generation"
        else:
            confidence = 70
            rationale = "PRD recommended as baseline documentation even with limited context"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.PRD.value,
            confidence=confidence,
            rationale=rationale,
            recommended=True
        )

    def _recommend_capabilities(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """Capabilities recommended when requirements are well-defined"""
        req_count = signals.get("requirement_count", 0)

        if req_count >= 5:
            confidence = 90
            rationale = f"Rich functional requirements ({req_count} identified) justify capability mapping"
        elif req_count >= 3:
            confidence = 75
            rationale = f"Moderate requirements ({req_count} identified) support capability structure"
        elif signals["has_requirements"]:
            confidence = 60
            rationale = "Some requirements present but may need more detail for comprehensive capability map"
        else:
            confidence = 40
            rationale = "Limited requirements; capability mapping may be premature"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.CAPABILITIES.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def _recommend_capability_cards(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """Capability cards recommended for complex capability maps"""
        req_count = signals.get("requirement_count", 0)

        if req_count >= 8:
            confidence = 85
            rationale = f"High requirement count ({req_count}) warrants detailed capability cards"
        elif req_count >= 5:
            confidence = 70
            rationale = f"Moderate complexity ({req_count} requirements) benefits from capability cards"
        elif req_count >= 3:
            confidence = 55
            rationale = "Capability cards useful but not essential at this complexity level"
        else:
            confidence = 35
            rationale = "Limited requirements; capability cards may add overhead"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.CAPABILITY_CARDS.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def _recommend_epics(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """Epics recommended for larger initiatives with multiple goals"""
        goal_count = signals.get("goal_count", 0)
        req_count = signals.get("requirement_count", 0)

        if goal_count >= 3 and req_count >= 5:
            confidence = 90
            rationale = f"Multiple goals ({goal_count}) and requirements ({req_count}) warrant epic-level planning"
        elif goal_count >= 2 or req_count >= 4:
            confidence = 75
            rationale = "Moderate scope justifies epic breakdown for organization"
        elif goal_count >= 1 or req_count >= 2:
            confidence = 55
            rationale = "Epics useful for structuring work but may be optional for small scope"
        else:
            confidence = 35
            rationale = "Limited scope; epics may be unnecessary overhead"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.EPICS.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def _recommend_features(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """Features recommended when epics are defined and requirements are detailed"""
        req_count = signals.get("requirement_count", 0)
        has_personas = signals.get("has_personas", False)

        if req_count >= 5 and has_personas:
            confidence = 85
            rationale = f"Detailed requirements ({req_count}) and defined personas enable feature specification"
        elif req_count >= 3:
            confidence = 70
            rationale = f"Requirements ({req_count}) support feature definition"
        elif req_count >= 1:
            confidence = 50
            rationale = "Basic requirements present; features help structure implementation"
        else:
            confidence = 30
            rationale = "Insufficient requirements for meaningful feature breakdown"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.FEATURES.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def _recommend_user_stories(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """User stories recommended for development-ready projects"""
        req_count = signals.get("requirement_count", 0)
        has_personas = signals.get("has_personas", False)
        technical_focus = signals.get("technical_focus", 0)

        if req_count >= 5 and has_personas and technical_focus >= 2:
            confidence = 80
            rationale = f"Development-ready: detailed requirements ({req_count}), personas, and technical context"
        elif req_count >= 4 and has_personas:
            confidence = 65
            rationale = "Good foundation for user stories but may need more technical detail"
        elif req_count >= 2:
            confidence = 45
            rationale = "Some requirements but may lack detail for actionable user stories"
        else:
            confidence = 25
            rationale = "Insufficient detail for development-level user stories"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.USER_STORIES.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def _recommend_lean_canvas(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """Lean Canvas recommended for business/strategic focus"""
        has_problem = signals.get("has_problem", False)
        business_focus = signals.get("business_focus", 0)

        if has_problem and business_focus >= 3:
            confidence = 85
            rationale = "Strong business focus with clear problem definition supports Lean Canvas"
        elif has_problem and business_focus >= 1:
            confidence = 70
            rationale = "Business context present; Lean Canvas useful for strategic planning"
        elif business_focus >= 2:
            confidence = 55
            rationale = "Some business focus but problem definition could be clearer"
        else:
            confidence = 40
            rationale = "Limited business/strategic context; Lean Canvas may not add value"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.LEAN_CANVAS.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def _recommend_technical_architecture(self, signals: Dict[str, Any]) -> ArtifactRecommendation:
        """Technical Architecture recommended when technical complexity is indicated"""
        req_count = signals.get("requirement_count", 0)
        technical_focus = signals.get("technical_focus", 0)
        has_requirements = signals.get("has_requirements", False)

        if technical_focus >= 3 and req_count >= 5:
            confidence = 90
            rationale = f"Strong technical focus ({technical_focus} indicators) with detailed requirements ({req_count}) warrants architecture diagram"
        elif technical_focus >= 2 and req_count >= 3:
            confidence = 80
            rationale = f"Technical context ({technical_focus} indicators) and requirements ({req_count}) support architecture documentation"
        elif technical_focus >= 1 or req_count >= 4:
            confidence = 65
            rationale = "Some technical context or requirements present; architecture diagram recommended for clarity"
        elif has_requirements:
            confidence = 55
            rationale = "Requirements present; architecture diagram useful for system design planning"
        else:
            confidence = 40
            rationale = "Limited technical context; architecture diagram may be premature"

        return ArtifactRecommendation(
            artifact_type=ArtifactType.TECHNICAL_ARCHITECTURE.value,
            confidence=confidence,
            rationale=rationale,
            recommended=confidence >= self.CONFIDENCE_MEDIUM
        )

    def get_recommended_artifacts(self) -> Set[str]:
        """
        Get set of recommended artifact types (confidence >= threshold).

        Returns:
            Set of artifact type names that are recommended
        """
        return {
            rec.artifact_type
            for rec in self.recommendations
            if rec.recommended
        }

    def save_recommendation_json(self, output_path: Path):
        """
        Save recommendations to JSON file.

        Args:
            output_path: Path to save recommendation.json
        """
        recommendation_data = {
            "recommendations": [asdict(rec) for rec in self.recommendations],
            "summary": {
                "total_artifacts": len(self.recommendations),
                "recommended": len([r for r in self.recommendations if r.recommended]),
                "high_confidence": len([r for r in self.recommendations if r.confidence >= self.CONFIDENCE_HIGH]),
                "medium_confidence": len([r for r in self.recommendations if self.CONFIDENCE_MEDIUM <= r.confidence < self.CONFIDENCE_HIGH]),
                "low_confidence": len([r for r in self.recommendations if r.confidence < self.CONFIDENCE_MEDIUM]),
            }
        }

        output_path.write_text(json.dumps(recommendation_data, indent=2), encoding='utf-8')
        LOG.info(f"Saved artifact recommendations to {output_path}")
        LOG.info(f"  Recommended: {recommendation_data['summary']['recommended']}/{recommendation_data['summary']['total_artifacts']}")
        LOG.info(f"  High confidence: {recommendation_data['summary']['high_confidence']}")
        LOG.info(f"  Medium confidence: {recommendation_data['summary']['medium_confidence']}")


def generate_recommendations(
    context_summary: str,
    output_dir: Path
) -> List[ArtifactRecommendation]:
    """
    Convenience function to generate and save artifact recommendations.

    Args:
        context_summary: The generated context summary markdown
        output_dir: Directory to save recommendation.json

    Returns:
        List of artifact recommendations
    """
    engine = RecommendationEngine()
    recommendations = engine.analyze_context(context_summary)
    engine.save_recommendation_json(output_dir / "recommendation.json")
    return recommendations
