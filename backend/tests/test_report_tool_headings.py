"""Contract tests for headings parsed by the report frontend."""

from app.services.zep_tools import (
    AgentInterview,
    InsightForgeResult,
    InterviewResult,
    PanoramaResult,
    SearchResult,
)


def test_search_result_uses_related_item_headings():
    text = SearchResult(
        facts=["A fact"],
        edges=[{"source": "A", "target": "B"}],
        nodes=[{"name": "A"}],
        query="What changes?",
        total_count=3,
    ).to_text()

    assert "### Search Query" in text
    assert "### Related Facts" in text
    assert "### Related Edges" in text
    assert "### Related Nodes" in text


def test_insight_and_panorama_results_use_frontend_contract_headings():
    insight = InsightForgeResult(
        query="What changes?",
        simulation_requirement="A policy changes",
        sub_queries=["Who responds?"],
        semantic_facts=["A fact"],
        entity_insights=[{"name": "A", "related_facts": ["A fact"]}],
        relationship_chains=["A -> B"],
    ).to_text()
    panorama = PanoramaResult(
        query="What changes?",
        active_facts=["A current fact"],
        historical_facts=["An older fact"],
    ).to_text()

    for heading in (
        "### Analysis Question",
        "### Prediction Scenario",
        "### Key Facts",
        "### Core Entities",
        "### Relationship Chains",
    ):
        assert heading in insight

    assert "### Search Query" in panorama
    assert "### Currently Valid Facts" in panorama


def test_interview_result_uses_frontend_contract_headings():
    interview = AgentInterview(
        agent_name="Jordan",
        agent_role="Researcher",
        agent_bio="Studies public response",
        question="What changes?",
        response="The response will likely vary by audience.",
        key_quotes=["The response will likely vary by audience."],
    )
    text = InterviewResult(
        interview_topic="Public response",
        interview_questions=["What changes?"],
        interviews=[interview],
        selection_reasoning="Relevant expertise",
        total_agents=1,
        interviewed_count=1,
    ).to_text()

    assert "### Interview Topic" in text
    assert "### Selection Rationale" in text
    assert "### Interview Transcript" in text
    assert "##### Key Quotes" in text
