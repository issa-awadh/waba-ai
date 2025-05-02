from dotenv import load_dotenv
load_dotenv('.env.local')
import os

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List, Dict, Any
import shutil
import os
import pdfplumber
from schemas import AnalyzeResponse, ExtractedFeatures, Recommendation, Product
import tempfile
import re
import logging
from faiss_agent import RagAgent, load_lab_report
import requests
import mypdf
from openai import OpenAI
from google import genai
import time
from requests.auth import HTTPBasicAuth
from fastapi import Body

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env.local')

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory recommendations store for demo (replace with DB in production)
recommendations_store = {
    "recommendations": None,
    "rationale": ""
}

# Routes
@app.get("/")
def read_root(status_code=200):
    return {"status": "ok", "message": "Product Recommendation API is running"}

@app.post("/extract-features", response_model=AnalyzeResponse)
async def extract_details_and_analyze(report: UploadFile = File(...), query: str = Form(...)):
    start_time = time.time()
    logging.info("Received request to /extract-features")
    print("Step 1: Start extract_details_and_analyze")
    print(f"Received file: {report.filename}")
    print(f"Received query: {query}")

    # Process the original filename
    original_name = report.filename
    name_no_ext = os.path.splitext(original_name)[0]
    clean_name = name_no_ext.strip().lower().replace(" ", "_")
    clean_name = clean_name + ".json"  # Remove special characters

    # Save the uploaded file to a temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            with open(temp_file_path, "wb") as f:
                shutil.copyfileobj(report.file, f)
        logging.info(f"Saved uploaded file to {temp_file_path}")
        print(f"Step 2: Saved uploaded file to {temp_file_path}")
    except Exception as e:
        logging.error(f"Error saving uploaded file: {e}")
        print(f"Error saving uploaded file: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

    # Extract features from the lab report using mypdf module
    try:
        logging.info("Extracting features from PDF")
        print("Step 3: Extracting features from PDF")
        lab_report = mypdf.extract_pdf_data(temp_file_path, clean_name)
    except Exception as e:
        logging.error(f"Error extracting features: {e}")
        print(f"Error extracting features: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        os.remove(temp_file_path)
        logging.info(f"Deleted temp file {temp_file_path}")
        print(f"Deleted temp file {temp_file_path}")

    # Analyze the extracted features using RagAgent
    def intialize_clients():
        logging.info("Initializing clients")
        print("Step 4: Initializing clients")
        # Initialize the clients here if needed
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
        return gpt_client, gemini_client, embedding_client

    try:
        gpt_client, gemini_client, embedding_client = intialize_clients()
        logging.info("Clients initialized successfully")
        print("Step 5: Clients initialized successfully")
        logging.info(f"Time elapsed after client init: {time.time() - start_time:.2f}s")
    except Exception as e:
        logging.error(f"Failed to initialize clients: {e}")
        print(f"Failed to initialize clients: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to initialize clients: {str(e)}"})

    try:
        logging.info("Initializing RagAgent")
        print("Step 6: Initializing RagAgent")
        agent = RagAgent(
                faiss_dir="FAISS",
                index_name="water-treatment",
                gpt_client=gpt_client,
                gemini_client=gemini_client,
                embedding_client=embedding_client,
                embedding_model="text-embedding-3-large",
                context_token_limit=100000,  # Increased context token limit
                docs_per_category=10,  # Retrieve more docs per category
                categories=[
                    "training", "ro", "pumps", "filters", "media",
                    "airblowers", "chemicals", "domestic", "dosage"
                ]
            )
        logging.info("RagAgent initialized successfully")
        print("Step 7: RagAgent initialized successfully")
        logging.info(f"Time elapsed after RagAgent init: {time.time() - start_time:.2f}s")
    except Exception as e:
        logging.error(f"Failed to initialize RagAgent: {e}")
        print(f"Failed to initialize RagAgent: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to initialize RagAgent: {str(e)}"})

    # Load the lab report JSON data
    try:
        logging.info("Loading lab report JSON")
        print("Step 8: Loading lab report JSON")
        # Fix: Use the correct function to load the lab report JSON from mypdf or faiss_agent
        # If mypdf does not have load_lab_report, use from faiss_agent import load_lab_report
        lab_report_json = load_lab_report('outputs/' + clean_name)
        logging.info("Lab report JSON loaded")
        print("Step 9: Lab report JSON loaded")
    except Exception as e:
        logging.error(f"Failed to load lab report: {e}")
        print(f"Failed to load lab report: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to load lab report: {str(e)}"})
    try:
        logging.info("Processing query with RagAgent")
        print("Step 10: Processing query with RagAgent")
        recommendation, rationale = agent.process(
            user_query=query,
            lab_report_json=lab_report_json,
            model_type="gemini",
            model_name="gemini-2.5-pro-exp-03-25",
            temperature=0.2,
            max_tokens=1500
        )
        logging.info("Query processed successfully")
        print("Step 11: Query processed successfully")
        logging.info(f"Time elapsed after agent.process: {time.time() - start_time:.2f}s")
    except Exception as e:
        logging.error(f"Failed to process query: {e}")
        print(f"Failed to process query: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to process query: {str(e)}"})
    print(recommendation.model_dump_json(indent=2))
    # Environment variables
    BASE_URL = os.getenv("BASE_URL")
    API_USERNAME = os.getenv("API_USERNAME")
    API_PASSWORD = os.getenv("API_PASSWORD")

    # # Add the price details from the erp system to the recommendation products
    # def get_product_details(no: str) -> dict:
    #     """Fetch comprehensive product details"""
    #     logging.info(f"Fetching product details for {no}")
    #     print(f"Fetching product details for {no}")
    #     params = {"$filter": f"No eq '{no}'"}
    #     try:
    #         response = requests.get(
    #             BASE_URL,
    #             params=params,
    #             auth=HTTPBasicAuth(API_USERNAME, API_PASSWORD)
    #         )
    #         response.raise_for_status()
    #         data = response.json()
            
    #         if 'value' in data and data['value']:
    #             item = data['value'][0]
    #             return {
    #                 'no': item.get('No', ''),
    #                 'inventory': int(item.get('Inventory', 0)),
    #                 'unit_price': float(item.get('Unit_Price', 0)),
    #                 'description': item.get('Description', ''),
    #                 'item_category_code': item.get('Item_Category_Code', ''),
    #                 'product_model': item.get('Product_Model', ''),
    #                 'specifications': item.get('Technical_Specifications', ''),
    #                 'warranty': item.get('Warranty_Period', '')
    #             }
    #         return {}
    #     except requests.RequestException as e:
    #         raise HTTPException(status_code=500, detail=f"Error fetching product details: {str(e)}")

    # def enrich_products_with_price(products: List[Product]) -> List[Product]:
    #     """Enrich the product objects with details from the API"""
    #     logging.info("Enriching products with price")
    #     print("Enriching products with price")
    #     enriched_products = []
    #     for product in products:
    #         details = get_product_details(product.model_number)
    #         if details:
    #             product.price = details.get('unit_price')
    #         enriched_products.append(product)
    #     return enriched_products

    # def enrich_recommendation(recommendation: Recommendation) -> Recommendation:
    #     """Enrich all products in a recommendation with details from the API"""
    #     logging.info("Enriching recommendation with product details")
    #     print("Enriching recommendation with product details")
    #     recommendation.pretreatment = enrich_products_with_price(recommendation.pretreatment)
    #     recommendation.RO = enrich_products_with_price(recommendation.RO)
    #     recommendation.postreatment = enrich_products_with_price(recommendation.postreatment)
    #     return recommendation

    # try:
    #     logging.info("Enriching recommendation")
    #     print("Step 12: Enriching recommendation")
    #     recommendation = enrich_recommendation(recommendation)
    #     logging.info("Recommendation enriched")
    #     print("Step 13: Recommendation enriched")
    #     logging.info(f"Time elapsed after enrichment: {time.time() - start_time:.2f}s")
    # except Exception as e:
    #     logging.error(f"Failed to enrich recommendation: {e}")
    #     print(f"Failed to enrich recommendation: {e}")
    #     return JSONResponse(status_code=500, content={"error": f"Failed to enrich recommendation: {str(e)}"})
    
    # Create the response object
    # Fix: Safely convert recommendation to dict for both Pydantic and plain dict cases
    if hasattr(recommendation, "dict"):
        rec = recommendation.dict()
    elif isinstance(recommendation, dict):
        rec = recommendation
    else:
        # fallback: try to convert to dict (e.g., dataclass)
        rec = dict(recommendation)

    # Normalize keys to match Pydantic schema
    if "RO" in rec:
        rec["ro"] = rec.pop("RO")
    if "postreatment" in rec:
        rec["posttreatment"] = rec.pop("postreatment")
    if "pretreatment" not in rec:
        rec["pretreatment"] = []
    if "ro" not in rec:
        rec["ro"] = []
    if "posttreatment" not in rec:
        rec["posttreatment"] = []

    # Ensure all product lists are lists of dicts (not custom objects)
    for key in ["pretreatment", "ro", "posttreatment"]:
        rec[key] = [
            p.dict() if hasattr(p, "dict") else dict(p) if not isinstance(p, dict) else p
            for p in rec[key]
        ]

    response = AnalyzeResponse(
        recommendations=rec,
        rationale=rationale
    )
    # Save to in-memory store for cart operations
    recommendations_store["recommendations"] = rec
    recommendations_store["rationale"] = rationale

    # Remove or comment out file save:
    # try:
    #     logging.info("Saving recommendation to file")
    #     print("Step 14: Saving recommendation to file")
    #     with open("recommendation.json", "w") as f:
    #         f.write(response.json(indent=2))
    #     logging.info("Recommendation saved to file")
    #     print("Step 15: Recommendation saved to file")
    # except Exception as e:
    #     logging.error(f"Failed to save recommendation: {e}")
    #     print(f"Failed to save recommendation: {e}")
    #     return JSONResponse(status_code=500, content={"error": f"Failed to save recommendation: {str(e)}"})
    try:
        logging.info("Returning response as JSON")
        print("Step 16: Returning response as JSON")
        logging.info(f"Total time for /extract-features: {time.time() - start_time:.2f}s")
        return JSONResponse(content=response.dict())
    except Exception as e:
        logging.error(f"Failed to return response: {e}")
        print(f"Failed to return response: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to return response: {str(e)}"})

# Endpoint to get current recommendations (for QuotationCart.vue)
@app.get("/api/recommendations")
def get_recommendations():
    return {
        "recommendations": recommendations_store["recommendations"],
        "rationale": recommendations_store["rationale"]
    }

# Endpoint to delete a product from recommendations
@app.post("/api/recommendations/delete")
def delete_recommendation(section: str = Body(...), model_number: str = Body(...)):
    rec = recommendations_store["recommendations"]
    if rec and section in rec:
        rec[section] = [p for p in rec[section] if p.get("model_number") != model_number]
        recommendations_store["recommendations"] = rec
    return {"success": True, "recommendations": rec}

# Endpoint to add a product to recommendations
@app.post("/api/recommendations/add")
def add_recommendation(section: str = Body(...), model_number: str = Body(...)):
    rec = recommendations_store["recommendations"]
    # Use your get_product_details logic here
    def get_product_details(no: str) -> dict:
        BASE_URL = os.getenv("BASE_URL")
        API_USERNAME = os.getenv("API_USERNAME")
        API_PASSWORD = os.getenv("API_PASSWORD")
        params = {"$filter": f"No eq '{no}'"}
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                auth=HTTPBasicAuth(API_USERNAME, API_PASSWORD)
            )
            response.raise_for_status()
            data = response.json()
            if 'value' in data and data['value']:
                item = data['value'][0]
                return {
                    'product_name': item.get('Description', ''),
                    'model_number': item.get('Product_Model', ''),
                    'category': item.get('Item_Category_Code', ''),
                    'price': float(item.get('Unit_Price', 0)),
                    'product_description': item.get('Technical_Specifications', ''),
                }
            return {}
        except Exception as e:
            return {}

    product = get_product_details(model_number)
    if product and rec and section in rec:
        rec[section].append(product)
        recommendations_store["recommendations"] = rec
    return {"success": True, "recommendations": rec}

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)