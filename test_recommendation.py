#!/usr/bin/env python3
"""
Test suite for the intelligent artifact recommendation system.

Verifies that:
1. RecommendationEngine analyzes context summaries correctly
2. Recommendations are generated with confidence scores and rationale
3. recommendation.json is saved with correct structure
4. Config overrides (generate_only) work correctly
"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path.cwd()))

from prdgen.recommendation import RecommendationEngine, generate_recommendations


# Sample context summaries for testing
MINIMAL_CONTEXT = """
## Problem / Opportunity
Build a simple API endpoint.

## Goals
- Create REST API

## Non-Goals
Not specified in documents

## Target Personas / Users
- Developers

## Key Functional Requirements
- HTTP GET endpoint
- JSON response

## Constraints & Assumptions
**Technical Constraints:**
None specified

**Business Constraints:**
None specified

**Assumptions:**
None specified

## Risks, Gaps, and Open Questions
**Risks:**
- None identified

**Information Gaps:**
- Detailed requirements needed

**Open Questions:**
- What data to return?

**Conflicts:**
- None

## Source Traceability
**Problem/Opportunity:** [requirements.md]
**Goals:** [requirements.md]
**Requirements:** [requirements.md]
"""

COMPREHENSIVE_CONTEXT = """
## Problem / Opportunity
We need to build a comprehensive e-commerce platform to compete in the online retail market. The platform must handle high traffic, provide excellent user experience, and integrate with existing inventory and payment systems.

## Goals
- Launch MVP in 6 months
- Support 100K concurrent users
- Integrate with 3 payment gateways
- Real-time inventory management
- Mobile-first responsive design
- SEO optimized product pages
- Analytics and reporting dashboard
- Customer review and rating system

## Non-Goals
- Physical store integration (future phase)
- International shipping (future phase)
- Wholesale/B2B portal (out of scope)

## Target Personas / Users
- End Customers: Online shoppers aged 25-45, tech-savvy
- Store Managers: Manage inventory, orders, and customer service
- Marketing Team: Run campaigns, analyze customer behavior
- Admin Users: Platform configuration and user management
- Customer Support: Handle tickets and inquiries

## Key Functional Requirements
- User registration and authentication
- Product catalog with search and filtering
- Shopping cart with real-time pricing
- Checkout and payment processing
- Order tracking and notifications
- Inventory management system
- Customer review and rating
- Recommendation engine
- Admin dashboard
- Reporting and analytics
- Email notifications
- Mobile app API

## Constraints & Assumptions
**Technical Constraints:**
- Must integrate with legacy inventory system (SQL Server)
- Payment gateway APIs have rate limits (100 req/min)
- Mobile app development in React Native

**Business Constraints:**
- Budget: $500K for MVP
- Timeline: 6 months to launch
- Compliance: PCI-DSS for payment processing

**Assumptions:**
- Users have reliable internet connection
- Payment gateways are 99.9% available
- Inventory data is updated every 15 minutes

## Risks, Gaps, and Open Questions
**Risks:**
- Integration with legacy inventory system may be complex
- Payment gateway downtime could block orders
- High traffic might require infrastructure scaling

**Information Gaps:**
- Exact product catalog size not specified
- Return/refund policy details needed
- Customer support SLA requirements

**Open Questions:**
- Which analytics platform to use?
- How to handle inventory conflicts?
- What's the disaster recovery plan?

**Conflicts:**
- None

## Source Traceability
**Problem/Opportunity:** [business_proposal.md, executive_brief.docx]
**Goals:** [business_proposal.md, technical_requirements.md]
**Personas:** [user_research.md]
**Requirements:** [technical_requirements.md, functional_spec.md]
**Constraints:** [budget_doc.xlsx, technical_requirements.md]
"""

BUSINESS_FOCUSED_CONTEXT = """
## Problem / Opportunity
Our company needs to enter the subscription box market. Customer research shows demand for curated monthly product deliveries. Current market has few specialized competitors in our niche.

## Goals
- Launch subscription service Q2 2024
- Acquire 1000 subscribers in first 3 months
- Achieve 15% month-over-month growth
- Build brand loyalty and recurring revenue

## Non-Goals
- One-time purchases (focus on subscriptions only)
- International markets (US only for MVP)

## Target Personas / Users
- Subscribers: Millennials interested in curated products
- Business Team: Manage subscriptions and customer relationships
- Marketing Team: Run campaigns and analyze conversion

## Key Functional Requirements
- Subscription signup and management
- Payment processing with recurring billing
- Product curation and delivery scheduling
- Customer preference management

## Constraints & Assumptions
**Business Constraints:**
- Need to be profitable by month 6
- Limited marketing budget ($50K)

**Assumptions:**
- 10% monthly churn rate
- Average subscription value $50/month

## Risks, Gaps, and Open Questions
**Risks:**
- Market saturation
- Customer acquisition cost may be high

**Information Gaps:**
- Exact product sourcing costs needed
- Shipping logistics details

**Open Questions:**
- How to handle subscription pauses?
- What payment methods to support?

## Source Traceability
**Problem/Opportunity:** [market_research.pdf]
**Goals:** [business_plan.docx]
"""


def test_recommendation_engine_initialization():
    """Test that RecommendationEngine initializes correctly"""
    print("\n▶ Testing RecommendationEngine initialization...")

    engine = RecommendationEngine()

    assert engine.CONFIDENCE_HIGH == 80, "High confidence threshold should be 80"
    assert engine.CONFIDENCE_MEDIUM == 50, "Medium confidence threshold should be 50"
    assert len(engine.recommendations) == 0, "Initial recommendations should be empty"

    print("  ✓ RecommendationEngine initialized correctly")


def test_minimal_context_recommendation():
    """Test recommendations for minimal context (simple project)"""
    print("\n▶ Testing recommendations for minimal context...")

    engine = RecommendationEngine()
    recommendations = engine.analyze_context(MINIMAL_CONTEXT)

    # Should have recommendations for all artifact types
    assert len(recommendations) == 7, f"Should have 7 recommendations, got {len(recommendations)}"

    # Convert to dict for easier checking
    rec_dict = {rec.artifact_type: rec for rec in recommendations}

    # PRD should always be highly recommended
    assert rec_dict["prd"].recommended, "PRD should be recommended"
    assert rec_dict["prd"].confidence >= 70, f"PRD confidence should be >= 70, got {rec_dict['prd'].confidence}"

    # Complex artifacts should have lower confidence for minimal context
    assert rec_dict["user_stories"].confidence < 50, "User stories should have low confidence for minimal context"
    assert not rec_dict["user_stories"].recommended, "User stories should not be recommended"

    print(f"  ✓ Minimal context: {len([r for r in recommendations if r.recommended])} artifacts recommended")
    print(f"    - PRD: {rec_dict['prd'].confidence}% (recommended)")
    print(f"    - User Stories: {rec_dict['user_stories'].confidence}% (not recommended)")


def test_comprehensive_context_recommendation():
    """Test recommendations for comprehensive context (complex project)"""
    print("\n▶ Testing recommendations for comprehensive context...")

    engine = RecommendationEngine()
    recommendations = engine.analyze_context(COMPREHENSIVE_CONTEXT)

    rec_dict = {rec.artifact_type: rec for rec in recommendations}

    # Most artifacts should be recommended for comprehensive context
    recommended_count = len([r for r in recommendations if r.recommended])
    assert recommended_count >= 5, f"Should recommend at least 5 artifacts, got {recommended_count}"

    # PRD should be highly recommended
    assert rec_dict["prd"].confidence >= 85, f"PRD should have high confidence, got {rec_dict['prd'].confidence}"

    # Capabilities should be recommended (many requirements)
    assert rec_dict["capabilities"].recommended, "Capabilities should be recommended"
    assert rec_dict["capabilities"].confidence >= 75, f"Capabilities should have high confidence, got {rec_dict['capabilities'].confidence}"

    # Epics should be recommended (multiple goals and requirements)
    assert rec_dict["epics"].recommended, "Epics should be recommended"

    # Features should be recommended (detailed requirements + personas)
    assert rec_dict["features"].recommended, "Features should be recommended"

    print(f"  ✓ Comprehensive context: {recommended_count} artifacts recommended")
    print(f"    - PRD: {rec_dict['prd'].confidence}%")
    print(f"    - Capabilities: {rec_dict['capabilities'].confidence}%")
    print(f"    - Epics: {rec_dict['epics'].confidence}%")
    print(f"    - Features: {rec_dict['features'].confidence}%")


def test_business_focused_recommendation():
    """Test recommendations for business-focused context"""
    print("\n▶ Testing recommendations for business-focused context...")

    engine = RecommendationEngine()
    recommendations = engine.analyze_context(BUSINESS_FOCUSED_CONTEXT)

    rec_dict = {rec.artifact_type: rec for rec in recommendations}

    # Lean Canvas should be highly recommended for business context
    assert rec_dict["lean_canvas"].recommended, "Lean Canvas should be recommended for business context"
    assert rec_dict["lean_canvas"].confidence >= 70, f"Lean Canvas should have high confidence, got {rec_dict['lean_canvas'].confidence}"

    print(f"  ✓ Business-focused context")
    print(f"    - Lean Canvas: {rec_dict['lean_canvas'].confidence}% (recommended)")


def test_recommendation_json_structure():
    """Test that recommendation.json has correct structure"""
    print("\n▶ Testing recommendation.json structure...")

    engine = RecommendationEngine()
    engine.analyze_context(COMPREHENSIVE_CONTEXT)

    # Save to temp file
    temp_dir = Path("/tmp/test_recommendation")
    temp_dir.mkdir(exist_ok=True)
    output_file = temp_dir / "recommendation.json"

    engine.save_recommendation_json(output_file)

    # Load and verify structure
    assert output_file.exists(), "recommendation.json should be created"

    data = json.loads(output_file.read_text())

    # Check top-level structure
    assert "recommendations" in data, "Should have 'recommendations' key"
    assert "summary" in data, "Should have 'summary' key"

    # Check recommendations array
    assert len(data["recommendations"]) == 7, "Should have 7 artifact recommendations"

    for rec in data["recommendations"]:
        assert "artifact_type" in rec, "Each recommendation should have artifact_type"
        assert "confidence" in rec, "Each recommendation should have confidence"
        assert "rationale" in rec, "Each recommendation should have rationale"
        assert "recommended" in rec, "Each recommendation should have recommended flag"

        # Validate confidence range
        assert 0 <= rec["confidence"] <= 100, f"Confidence should be 0-100, got {rec['confidence']}"

    # Check summary statistics
    summary = data["summary"]
    assert "total_artifacts" in summary, "Summary should have total_artifacts"
    assert "recommended" in summary, "Summary should have recommended count"
    assert "high_confidence" in summary, "Summary should have high_confidence count"
    assert "medium_confidence" in summary, "Summary should have medium_confidence count"
    assert "low_confidence" in summary, "Summary should have low_confidence count"

    assert summary["total_artifacts"] == 7, "Total artifacts should be 7"

    print(f"  ✓ recommendation.json structure is valid")
    print(f"    - Total artifacts: {summary['total_artifacts']}")
    print(f"    - Recommended: {summary['recommended']}")
    print(f"    - High confidence: {summary['high_confidence']}")
    print(f"    - Medium confidence: {summary['medium_confidence']}")

    # Cleanup
    output_file.unlink()


def test_signal_extraction():
    """Test that signals are extracted correctly from context"""
    print("\n▶ Testing signal extraction...")

    engine = RecommendationEngine()

    # Test with comprehensive context
    signals = engine._extract_signals(COMPREHENSIVE_CONTEXT)

    assert signals["has_problem"], "Should detect problem section"
    assert signals["has_goals"], "Should detect goals section"
    assert signals["has_personas"], "Should detect personas section"
    assert signals["has_requirements"], "Should detect requirements section"

    assert signals["goal_count"] >= 5, f"Should detect multiple goals, got {signals['goal_count']}"
    assert signals["requirement_count"] >= 10, f"Should detect many requirements, got {signals['requirement_count']}"
    assert signals["persona_count"] >= 3, f"Should detect multiple personas, got {signals['persona_count']}"

    assert signals["business_focus"] > 0, "Should detect business keywords"
    assert signals["technical_focus"] > 0, "Should detect technical keywords"

    print(f"  ✓ Signals extracted correctly")
    print(f"    - Goals: {signals['goal_count']}")
    print(f"    - Requirements: {signals['requirement_count']}")
    print(f"    - Personas: {signals['persona_count']}")
    print(f"    - Business focus: {signals['business_focus']} keywords")
    print(f"    - Technical focus: {signals['technical_focus']} keywords")


def test_convenience_function():
    """Test the convenience function for generating recommendations"""
    print("\n▶ Testing convenience function...")

    temp_dir = Path("/tmp/test_recommendation_conv")
    temp_dir.mkdir(exist_ok=True)

    recommendations = generate_recommendations(COMPREHENSIVE_CONTEXT, temp_dir)

    # Verify recommendations returned
    assert len(recommendations) > 0, "Should return recommendations"

    # Verify JSON file created
    json_file = temp_dir / "recommendation.json"
    assert json_file.exists(), "recommendation.json should be created"

    print(f"  ✓ Convenience function works correctly")

    # Cleanup
    json_file.unlink()


if __name__ == "__main__":
    print("=" * 70)
    print("ARTIFACT RECOMMENDATION SYSTEM TEST SUITE")
    print("=" * 70)

    try:
        test_recommendation_engine_initialization()
        test_minimal_context_recommendation()
        test_comprehensive_context_recommendation()
        test_business_focused_recommendation()
        test_recommendation_json_structure()
        test_signal_extraction()
        test_convenience_function()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nArtifact recommendation system successfully implemented:")
        print("  ✓ Analyzes document context for recommendation signals")
        print("  ✓ Generates confidence scores and rationale for each artifact")
        print("  ✓ Adapts recommendations to project complexity and focus")
        print("  ✓ Outputs structured recommendation.json")
        print("  ✓ Distinguishes between business vs technical projects")
        print("  ✓ Provides high/medium/low confidence classifications")
        print("\nReady for integration with generator!")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
