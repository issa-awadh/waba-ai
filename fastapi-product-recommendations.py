from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Product Recommendation API", 
              description="API for managing treatment product recommendations")

# Configure CORS to allow requests from the Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Adjust based on your Vue app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
BASE_URL = os.getenv("BASE_URL")
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")

# Models
class Product(BaseModel):
    """Represents a Product to be used in the treatment pipeline."""
    product_description: str
    product_name: str
    model_number: str = Field(alias="model")
    price: Optional[float] = None

class Recommendation(BaseModel):
    """Recommendations for pretreatment, RO, and posttreatment products."""
    pretreatment: List[Product]
    RO: List[Product]
    postreatment: List[Product]
    
class RecommendationWithRationale(BaseModel):
    """Recommendations with the rationale used to make them."""
    recommendations: Recommendation
    rationale: str

class ProductSearchResponse(BaseModel):
    """Response model for product search results."""
    products: List[Product]
    
class ProductAddRequest(BaseModel):
    """Request model for adding a product to recommendations."""
    product: Product
    category: str  # 'pretreatment', 'RO', or 'postreatment'
    
class ProductRemoveRequest(BaseModel):
    """Request model for removing a product from recommendations."""
    model_number: str
    category: str  # 'pretreatment', 'RO', or 'postreatment'

# Helper functions
def get_product_details(no: str) -> dict:
    """Fetch comprehensive product details"""
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
                'no': item.get('No', ''),
                'inventory': int(item.get('Inventory', 0)),
                'unit_price': float(item.get('Unit_Price', 0)),
                'description': item.get('Description', ''),
                'item_category_code': item.get('Item_Category_Code', ''),
                'product_model': item.get('Product_Model', ''),
                'specifications': item.get('Technical_Specifications', ''),
                'warranty': item.get('Warranty_Period', '')
            }
        return {}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching product details: {str(e)}")

def enrich_products_with_price(products: List[Product]) -> List[Product]:
    """Enrich the product objects with details from the API"""
    enriched_products = []
    
    for product in products:
        details = get_product_details(product.model_number)
        if details:
            product.price = details.get('unit_price')
        
        enriched_products.append(product)
        
    return enriched_products

def enrich_recommendation(recommendation: Recommendation) -> Recommendation:
    """Enrich all products in a recommendation with details from the API"""
    recommendation.pretreatment = enrich_products_with_price(recommendation.pretreatment)
    recommendation.RO = enrich_products_with_price(recommendation.RO)
    recommendation.postreatment = enrich_products_with_price(recommendation.postreatment)
    return recommendation

# Mock database for recommendations
# In a real app, you'd use a database like MongoDB, PostgreSQL, etc.
sample_recommendation = Recommendation(
    pretreatment=[
        Product(product_name="Sediment Filter", product_description="5 micron sediment filter", model="SF-5000")
    ],
    RO=[
        Product(product_name="RO Membrane", product_description="100 GPD RO membrane", model="RO-100")
    ],
    postreatment=[
        Product(product_name="Carbon Filter", product_description="Post-treatment carbon filter", model="CF-2000")
    ]
)

sample_rationale = """
# Recommendation Rationale

## Water Quality Analysis
Based on the provided water quality parameters, we've identified high turbidity and mineral content.

## Treatment Approach
1. **Pretreatment**: Sediment filtration to remove particulates.
2. **RO Treatment**: Reverse osmosis to remove dissolved solids.
3. **Post-treatment**: Carbon filtration for taste and odor improvement.

These recommendations are optimized for your specific water conditions.
"""

# Routes
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Product Recommendation API is running"}

@app.get("/recommendations", response_model=RecommendationWithRationale)
def get_recommendations():
    """Get current recommendations with prices and rationale"""
    enriched_recommendation = enrich_recommendation(sample_recommendation)
    return RecommendationWithRationale(
        recommendations=enriched_recommendation,
        rationale=sample_rationale
    )

@app.get("/products/search", response_model=ProductSearchResponse)
def search_product(query: str = Query(..., description="Search query for products")):
    """Search for products that match the query"""
    # In a real app, you'd query your product database
    # For now, we'll use mock data
    mock_products = [
        Product(product_name="Sediment Filter 10 micron", product_description="Coarse sediment filter", model="SF-1000"),
        Product(product_name="Carbon Block Filter", product_description="Chlorine removal filter", model="CB-3000"),
        Product(product_name="RO Membrane 150 GPD", product_description="High capacity RO membrane", model="RO-150"),
        Product(product_name="UV Light System", product_description="UV disinfection system", model="UV-2000")
    ]
    
    # Filter products based on the query
    filtered_product = [p for p in mock_products if query.lower() in p.product_name.lower() or query.lower() in p.product_description.lower()]
    
    # Enrich products with details
    enriched_products = enrich_products_with_price(filtered_product)
    
    return ProductSearchResponse(products=enriched_products)

@app.post("/recommendations/add", response_model=Recommendation)
def add_product(request: ProductAddRequest):
    """Add a product to the recommendations"""
    # Validate the category
    if request.category not in ["pretreatment", "RO", "postreatment"]:
        raise HTTPException(status_code=400, detail="Invalid category. Must be 'pretreatment', 'RO', or 'postreatment'")
    
    # Add the product to the appropriate category
    if request.category == "pretreatment":
        sample_recommendation.pretreatment.append(request.product)
    elif request.category == "RO":
        sample_recommendation.RO.append(request.product)
    else:  # postreatment
        sample_recommendation.postreatment.append(request.product)
    
    # Return the updated recommendations
    return enrich_recommendation(sample_recommendation)

@app.post("/recommendations/remove", response_model=Recommendation)
def remove_product(request: ProductRemoveRequest):
    """Remove a product from the recommendations"""
    # Validate the category
    if request.category not in ["pretreatment", "RO", "postreatment"]:
        raise HTTPException(status_code=400, detail="Invalid category. Must be 'pretreatment', 'RO', or 'postreatment'")
    
    # Remove the product from the appropriate category
    if request.category == "pretreatment":
        sample_recommendation.pretreatment = [p for p in sample_recommendation.pretreatment if p.model_number != request.model_number]
    elif request.category == "RO":
        sample_recommendation.RO = [p for p in sample_recommendation.RO if p.model_number != request.model_number]
    else:  # postreatment
        sample_recommendation.postreatment = [p for p in sample_recommendation.postreatment if p.model_number != request.model_number]
    
    # Return the updated recommendations
    return enrich_recommendation(sample_recommendation)

@app.get("/product/{model_number}", response_model=Product)
def get_product(model_number: str):
    """Get details for a specific product by model number"""
    details = get_product_details(model_number)
    if not details:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create a product object from the details
    product = Product(
        product_name=details.get('description', ''),
        product_description=details.get('specifications', ''),
        model=model_number,
        price=details.get('unit_price'),
        inventory=details.get('inventory'),
        specifications=details.get('specifications'),
        warranty=details.get('warranty')
    )
    
    return product

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
