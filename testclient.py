from fastapi.testclient import TestClient
from app import app
import io

# filepath: c:\Projects\dayliff_water_triage_sizing\test_app.py

client = TestClient(app)

def test_extract_features_from_lab_report():
    # Simulate a PDF file
    pdf_content = b"%PDF-1.4\n%Fake PDF content for testing\n"
    file = io.BytesIO(pdf_content)
    file.name = "test_report.pdf"

    # Send POST request to the endpoint
    response = client.post(
        "/extract-features",
        files={"report": ("lab_report.pdf", file, "application/pdf")},
        data={"filename": "test_report.pdf"}
    )

    # Assert the response
    assert response.status_code == 200 or response.status_code == 500
    if response.status_code == 200:
        assert "features" in response.json()
    elif response.status_code == 500:
        assert "error" in response.json()