import os
import json
import faiss
from openai import OpenAI
from google import genai
from pydantic import BaseModel
from typing import List, Dict, Tuple, Optional
import numpy as np
import re
from faiss_agent import RagAgent, load_lab_report
from schemas import Product, Recommendation
# Initialize API clients with your API keys
# For OpenAI/GitHub models
gpt_client = OpenAI(
    base_url=github_endpoint,
    api_key=github_token,
)

# For Gemini model
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_api_key)

# For embeddings (using Azure OpenAI in this example)
azure_endpoint = "https://models.inference.ai.azure.com"
embedding_client = OpenAI(
    base_url=azure_endpoint,
    api_key=github_token,
)

def main():
    # Create the RagAgent with custom configuration
    agent = RagAgent(
        faiss_dir="FAISS",
        index_name="water-treatment",
        gpt_client=gpt_client,
        gemini_client=gemini_client,
        embedding_client=embedding_client,
        embedding_model="text-embedding-3-large",
        context_token_limit=100000,  # Increased context token limit
        docs_per_category=15,  # Retrieve more docs per category
        categories=[
            "training", "ro", "pumps", "filters", "media",
            "airblowers", "chemicals", "domestic", "dosage"
        ]
    )

    # Load lab report from JSON file
    lab_report_path = "tiffis_lab_report.json"
    try:
        lab_report_json = load_lab_report(lab_report_path)
        print(f"Successfully loaded lab report from {lab_report_path}")
    except Exception as e:
        print(f"Error loading lab report: {str(e)}")
        # Fallback to a minimal example
        lab_report_json = json.dumps({
            "site": "Sample Site",
            "source": "Borehole",
            "date": "2025-04-25",
            "parameters": [
                {"name": "TDS", "value": 1500, "unit": "mg/L", "standard": 1000},
                {"name": "pH", "value": 6.8, "unit": "", "standard": "6.5-8.5"},
                {"name": "Turbidity", "value": 5.2, "unit": "NTU", "standard": 5}
            ]
        })
        print("Using fallback lab report data")

    # Define user query
    user_query = """
    Please help with a design of a water treatment pipeline consisting of:
    pretreatment, reverse osmosis design, and posttreatment.

    A water purification plant for a borehole water source at a daily demand of 0.5m3/hr
    for domestic purposes. Include the type of airblowers, pumps, filters, antiscalant,
    chemicals, water treatment media, chemical dosage, products for pretreatment and
    postreatment, given the RO chosen as per the lab results.

    Suggest products from this given url: https://www.davisandshirtliff.com/products-and-solutions/
    to help make recommendations.
    """

    """# Process with GPT
    print("\n=== Processing with GPT ===")
    try:
        gpt_recommendation, gpt_explanation = agent.process(
            user_query=user_query,
            lab_report_json=lab_report_json,
            model_type="gpt",
            model_name="openai/gpt-4.1",  # Use the latest available model
            temperature=0.2,
            max_tokens=1500
        )

        print("\n=== GPT Recommendation ===")
        print(gpt_recommendation.model_dump_json(indent=2))
        print("\n=== GPT Explanation ===")
        print(gpt_explanation)

        # Save GPT results to files
        with open("gpt_recommendation.json", "w") as f:
            f.write(gpt_recommendation.model_dump_json(indent=2))
        with open("gpt_explanation.md", "w") as f:
            f.write(gpt_explanation)

    except Exception as e:
        print(f"Error processing with GPT: {str(e)}")"""

    # Process with Gemini
    print("\n=== Processing with Gemini ===")
    try:
        gemini_recommendation, gemini_explanation = agent.process(
            user_query=user_query,
            lab_report_json=lab_report_json,
            model_type="gemini",
            model_name="gemini-2.5-pro-exp-03-25",
            temperature=0.2,
            max_tokens=1500
        )

        print("\n=== Gemini Recommendation ===")
        if gemini_recommendation:
            print(gemini_recommendation.model_dump_json(indent=2))
            # Save Gemini results to files
            with open("gemini_recommendation.json", "w") as f:
                f.write(gemini_recommendation.model_dump_json(indent=2))
        else:
            print("Failed to parse structured recommendation")

        print("\n=== Gemini Explanation ===")
        print(gemini_explanation)

        with open("gemini_explanation.md", "w") as f:
            f.write(gemini_explanation)

    except Exception as e:
        print(f"Error processing with Gemini: {str(e)}")

    """# Compare recommendations (if both are available)
    if 'gpt_recommendation' in locals() and 'gemini_recommendation' in locals() and gemini_recommendation:
        print("\n=== Model Comparison ===")
        print("Pretreatment products:")
        print(f"  GPT: {len(gpt_recommendation.pretreatment)} products")
        print(f"  Gemini: {len(gemini_recommendation.pretreatment)} products")

        print("\nRO products:")
        print(f"  GPT: {len(gpt_recommendation.RO)} products")
        print(f"  Gemini: {len(gemini_recommendation.RO)} products")

        print("\nPosttreatment products:")
        print(f"  GPT: {len(gpt_recommendation.postreatment)} products")
        print(f"  Gemini: {len(gemini_recommendation.postreatment)} products")"""

if __name__ == "__main__":
    main()