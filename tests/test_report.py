from io import BytesIO

from pypdf import PdfReader

from core.alarm_events import build_alarm_events
from core.database import query_alarms, query_running
from core.diagnosis import diagnose
from core.report import generate_running_report
from core.scenario import run_scenario


def test_pdf_running_report_is_generated(isolated_db):
    run_scenario(seed=17)
    running = query_running(100, ascending=True)
    alarms = query_alarms(20)
    events = build_alarm_events(alarms, running)
    diagnosis = diagnose(running.tail(3).to_dict("records"))

    pdf = generate_running_report(
        device_id="PUMP-001",
        start_date="2026-11-12",
        end_date="2026-11-12",
        running=running,
        alarm_events=events,
        diagnosis=diagnosis,
        health_score=96,
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 3000
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) >= 1
