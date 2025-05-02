from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Product(BaseModel):
    """Represents a Product to be used in the treatment pipeline."""
    product_description: str
    product_name: str
    model_number: str #= Field(alias="model")
    category: str
    price: Optional[float] = None #= Field(default=None, alias="price")

class Recommendation(BaseModel):
    pretreatment: List[Product]
    ro: List[Product]
    posttreatment: List[Product]

class AnalyzeResponse(BaseModel):
    recommendations: Recommendation
    rationale: str 

class ExtractedFeatures(BaseModel):
    """Represents the extracted features from the lab report."""
    features: Dict[str, Any]
    json_path: str