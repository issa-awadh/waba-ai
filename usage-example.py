import os
import chromadb
from openai import OpenAI
from google import genai
from rag_agent_fixed import RagAgent, load_lab_report

# Ensure you have the required environment variables set
from dotenv import load_dotenv
load_dotenv()

# Initialize clients with your API keys
# For GitHub-hosted model
github_token = os.environ.get("GITHUB_TOKEN")
github_endpoint = os.environ.get("GITHUB_ENDPOINT")
gpt_client = OpenAI(
    base_url=github_endpoint,
    api_key=github_token,
)

# For Gemini model
gemini_api_key = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_api_key)

# For embeddings (using same GitHub client in this example)
azure_endpoint = os.environ.get("AZURE_ENDPOINT")
embedding_client = OpenAI(
    base_url=azure_endpoint,
    api_key=github_token,
)

# Initialize ChromaDB client
chroma_path = "ChromaDB_1745774716"  # Update with your path
chroma_client = chromadb.PersistentClient(path=chroma_path)
collection_name = "water-treatment"

# Create the RagAgent with custom configuration
agent = RagAgent(
    chroma_client=chroma_client,
    collection_name=collection_name,
    gpt_client=gpt_client,
    gemini_client=gemini_client,
    embedding_client=embedding_client,
    embedding_model="text-embedding-3-large",
    context_token_limit=8000,  # Increase context token limit
    docs_per_category=4,  # Retrieve more docs per category
    categories=[
        "training", "ro", "pumps", "filters", "media",
        "airblowers", "chemicals", "domestic", "dosage"
    ]
)

# Load lab report
lab_report_json = load_lab_report("tiffis_lab_report.json")

# Define user query
user_query = """
Please help with a design of a water treatment pipeline consisting of: pretreatment, 
reverse osmosis design, and posttreatment. A water purification plant for a borehole 
water source at a daily demand of 0.5m3/hr for domestic purposes. Include the type of 
airblowers, pumps, filters, antiscalant, chemicals, water treatment media, chemical 
dosage, products for pretreatment and postreatment, given the RO chosen as per the lab results.
Suggest products from this given url: https://www.davisandshirtliff.com/products-and-solutions/ 
to help make recommendations.
"""

"""
# Process the query using GPT
recommendation, explanation = agent.process(
    user_query=user_query,
    lab_report_json=lab_report_json,
    model_type="gpt",
    model_name="openai/gpt-4.1",
    temperature=0.2,
    max_tokens=1500
)

# Print results
print("=== GPT Recommendation ===")
print(recommendation.model_dump_json(indent=2))
print("\n=== Explanation ===")
print(explanation)"""

# Alternatively, use Gemini
gemini_recommendation, gemini_explanation = agent.process(
    user_query=user_query,
    lab_report_json=lab_report_json,
    model_type="gemini",
    model_name="gemini-2.5-pro-exp-03-25"
)

print("\n=== Gemini Recommendation ===")
if gemini_recommendation:
    print(gemini_recommendation.model_dump_json(indent=2))
else:
    print("Failed to parse structured recommendation")
print("\n=== Gemini Explanation ===")
print(gemini_explanation)
