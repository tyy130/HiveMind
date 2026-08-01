from app import create_app
from app.config import Config
from app.services.report_agent import ReportAgent, ReportManager, ReportStatus


def test_report_api_does_not_expose_unexpected_exception_details(monkeypatch):
    sentinel = "SECRET-PROVIDER-BODY /srv/private/report.json"

    def fail_get_report(_cls, _report_id):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(
        ReportManager,
        "get_report",
        classmethod(fail_get_report),
    )

    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get(
        "/api/report/report_test",
        headers={"Accept-Language": "en"},
    )

    assert response.status_code == 500
    assert response.json == {
        "success": False,
        "error": "Unknown error",
    }
    assert sentinel not in response.get_data(as_text=True)
    assert "traceback" not in response.json


def test_failed_report_artifacts_do_not_expose_provider_exception(tmp_path, monkeypatch):
    sentinel = "SECRET-PROVIDER-BODY /srv/private/report.json"
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(Config, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_dir))

    class FailingLLM:
        def chat_json(self, **_kwargs):
            raise RuntimeError(sentinel)

        def chat(self, **_kwargs):
            raise RuntimeError(sentinel)

    agent = ReportAgent(
        graph_id="graph_test",
        simulation_id="simulation_test",
        simulation_requirement="Test safe failures",
        llm_client=FailingLLM(),
        zep_tools=object(),
    )
    report = agent.generate_report(report_id="report_safe_failure")

    assert report.status == ReportStatus.FAILED
    assert report.error == "未知错误"

    report_artifacts = [
        path.read_text(encoding="utf-8")
        for path in (reports_dir / report.report_id).iterdir()
        if path.is_file()
    ]
    assert report_artifacts
    assert all(sentinel not in contents for contents in report_artifacts)
