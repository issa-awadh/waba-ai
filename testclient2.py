import pytest
from testclient import test_extract_features_from_lab_report
from fastapi.testclient import TestClient
from app import app
import io
from pprint import pprint
# filepath: c:\Projects\dayliff_water_triage_sizing\test_testclient.py

client = TestClient(app)

def test_test_extract_features_from_lab_report():
    # Simulate the actual PDF file
    with open("TIFFIS BEACH HOUSE WATER ANALYSIS REPORT.pdf", "rb") as file:
        pdf_content = file.read()
    file = io.BytesIO(pdf_content)
    file.name = "tiffis_beach_house_water_analysis_report.pdf"  # Set the name of the BytesIO object

    # Send POST request to the endpoint
    response = client.post(
        "/extract-features",
        files={"report": ( file.name, file, "application/pdf")},
    )
    # ...existing code...
    print("Status code:", response.status_code)
    print(f"Response JSON: {response.json()}")
    # Assert the response
    assert response.status_code == 200 or response.status_code == 500
    if response.status_code == 200:
        assert "features" in response.json()
    elif response.status_code == 500:
        assert "error" in response.json()
    print("Test completed successfully.")