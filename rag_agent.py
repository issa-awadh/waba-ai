import os
import json
import re
from typing import List, Dict, Tuple, Optional, Union, Any
from pydantic import BaseModel, Field
import tiktoken
from openai import OpenAI
from google import genai
import chromadb

class Product(BaseModel):
    """Represents a Product to be used in the treatment pipeline."""
    product_description: str
    product_name: str
    model_number: str #= Field(alias="model")
    

class Recommendation(BaseModel):
    """Recommendations for pretreatment, RO, and posttreatment products."""
    pretreatment: List[Product]
    RO: List[Product]
    postreatment: List[Product]

class RagAgent:
    """
    Retrieval Augmented Generation (RAG) agent for water treatment recommendations.
    
    This class handles:
    1. Query processing and vectorization
    2. Contextual retrieval from ChromaDB
    3. LLM inference using GPT or Gemini models
    4. Response parsing and formatting
    """
    
    def __init__(
        self,
        chroma_client,
        collection_name: str,
        gpt_client = None,
        gemini_client = None,
        embedding_client = None,
        embedding_model: str = "text-embedding-3-large",
        context_token_limit: int = 6700,
        docs_per_category: int = 3,
        categories: List[str] = None
    ):
        """
        Initialize the RAG agent with clients and configuration.
        
        Args:
            chroma_client: Initialized ChromaDB client
            collection_name: Name of the collection to query
            gpt_client: OpenAI client for GPT models
            gemini_client: Google Generative AI client for Gemini models
            embedding_client: Client for generating embeddings
            embedding_model: Name of the embedding model to use
            context_token_limit: Maximum tokens for context
            docs_per_category: Number of documents to retrieve per category
            categories: List of categories to query (defaults to standard set if None)
        """
        self.chroma_client = chroma_client
        self.collection = chroma_client.get_collection(collection_name)
        self.gpt_client = gpt_client
        self.gemini_client = gemini_client
        self.embedding_client = embedding_client or gpt_client
        self.embedding_model = embedding_model
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.context_token_limit = context_token_limit
        self.docs_per_category = docs_per_category
        self.categories = categories or [
            "training", "ro", "pumps", "filters", "media",
            "airblowers", "chemicals", "domestic", "dosage"
        ]
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using the tokenizer."""
        return len(self.tokenizer.encode(text))
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using specified client."""
        response = self.embedding_client.embeddings.create(
            input=[text],
            model=self.embedding_model
        )
        return response.data[0].embedding
    
    def get_top_k(self, category: str, query_embedding: List[float], k: int) -> Dict:
        """Retrieve top k documents for a category."""
        # Special case for training materials which might need more results
        if category == "training":
            return self.collection.query(
                query_embeddings=[query_embedding],
                n_results=20,
                where={"category": category},
                include=["documents", "metadatas", "distances"]
            )
        
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"category": category},
            include=["documents", "metadatas", "distances"]
        )
    
    def build_context(self, search_query: str) -> str:
        """
        Build retrieval context by querying across multiple categories.
        
        Args:
            search_query: Processed search query for retrieval
            
        Returns:
            String containing formatted context from retrieved documents
        """
        query_embedding = self.get_embedding(search_query)
        parts, total_tokens = [], 0
        
        for cat in self.categories:
            try:
                # Get top documents for this category
                results = self.get_top_k(cat, query_embedding, self.docs_per_category)
                
                if not results or len(results["documents"]) == 0 or len(results["documents"][0]) == 0:
                    continue
                    
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                dists = results["distances"][0]
                
                for doc, md, dist in zip(docs, metas, dists):
                    # Format header with category and relevance score
                    header = f"\n## {cat.title()} (rel={1 - dist/2:.2f})\n"
                    snippet = doc
                    
                    # Truncate by token budget
                    remain = self.context_token_limit - total_tokens - len(self.tokenizer.encode(header))
                    if remain <= 0:
                        break
                        
                    tokens = self.tokenizer.encode(snippet)[:remain]
                    snippet = self.tokenizer.decode(tokens)
                    
                    part = header + snippet + "\n"
                    
                    """"
                    # Include metadata where available
                    if md.get("summary"):
                        part += f"Summary: {md['summary']}\n"
                    else:
                        qblock = md.get("questions_this_excerpt_can_answer", "")
                        if qblock:
                            cleaned = re.sub(r'<think>.*?</think>', '', qblock, flags=re.DOTALL).strip()
                            part += f"Questions: {cleaned[:500]}\n"
                    
                    parts.append(part)
                    total_tokens += len(self.tokenizer.encode(part))
                    """
                if total_tokens >= self.context_token_limit:
                    break
                    
            except Exception as e:
                parts.append(f"\n## Error retrieving {cat}: {str(e)}\n")
        
        return "\n".join(parts)
    
    def generate_search_query(self, lab_json: str, user_query: str, model: str = "openai/gpt-4.1-mini") -> str:
        """
        Generate optimized search query from lab report and user request.
        
        Args:
            lab_json: JSON string containing water lab analysis
            user_query: Original user query
            model: Model to use for query generation
            
        Returns:
            Optimized search query for retrieval
        """
        system_prompt = (
            "You are an AI assistant that converts a JSON-formatted water lab report into a concise, "
            "action-oriented search query for semantic retrieval from a ChromaDB of water-treatment equipment "
            "and design guides. When you receive a JSON input, you must:\n"
            "1. Extract and name the site location, source and analysis date.\n"
            "2. List each parameter that exceeds WHO guidelines, giving its name, unit, and value.\n"
            "3. Summarize in keyword form the recommended treatment stages under three headings:\n"
            "   - Pretreatment - Pre-treatment to be done before the RO (e.g. coagulation, sedimentation, multimedia filtration)\n"
            "   - RO Type  (e.g. 250 L/hr high-pressure pump, high-TDS membranes @30 bar)\n"
            "   - Posttreatment (e.g. cation-exchange softener, Mn/Cu adsorption, airblower)\n"
            "   - Comments: (e.g. \High TDS 18810 & EC 26490: require 250 L/hr RO with 30–40 bar high-pressure pump + antiscalant dosing; 3250 mg/L hardness: add cation-exchange softener; Mn 0.17 & Cu 4.18: install metal-specific adsorption resin; Turbidity 6 NTU: coagulation + multimedia filtration\)\n"
            "\nInclude exact numeric constraints in your search query, e.g. 'RO 250 L/hr @30 bar pump', 'pump >=250 lph'."
            "Output only one short paragraph or one comma-separated string of keywords that combines these elements, "
            "optimized for embedding (no extra explanation, no JSON). Keep it under 600 words."
        )
        
        user_prompt = (
            f"{user_query}\n"
            "Please transform the following water lab report (JSON) into a concise search query as per the system instructions.\n"
            "```json\n"
            f"{lab_json}\n"
            "```"
        )
        
        response = self.gpt_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.0
        )
        
        return response.choices[0].message.content
    
    def extract_json_and_markdown(self, response_text: str) -> Tuple[str, str]:
        """
        Extract JSON and markdown parts from model response.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Tuple of (json_string, markdown_explanation)
        """
        # Try to find JSON block using regex patterns for code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            json_part = json_match.group(1).strip()
            # Remove the JSON block to get markdown
            markdown_part = re.sub(r'```(?:json)?\s*[\s\S]*?\s*```', '', response_text, 1).strip()
            return json_part, markdown_part
        
        # Try to find first JSON object with opening/closing braces
        json_match = re.search(r'(\{[\s\S]*\})', response_text)
        if json_match:
            json_part = json_match.group(1).strip()
            # Get everything after the JSON
            parts = response_text.split(json_match.group(1), 1)
            markdown_part = parts[1].strip() if len(parts) > 1 else ""
            return json_part, markdown_part
        
        # Try finding JSON after a marker like "JSON:" or "JSON Object:"
        json_marker_match = re.search(r'(?:JSON|JSON Object|JSON Response):\s*(\{[\s\S]*\})', response_text, re.IGNORECASE)
        if json_marker_match:
            json_part = json_marker_match.group(1).strip()
            # Get content after the JSON
            parts = response_text.split(json_part, 1)
            markdown_part = parts[1].strip() if len(parts) > 1 else ""
            return json_part, markdown_part
        
        # Fallback: try splitting by double newline and assume first part is JSON
        parts = response_text.split("\n\n", 1)
        if len(parts) == 2 and parts[0].strip().startswith('{') and parts[0].strip().endswith('}'):
            return parts[0].strip(), parts[1].strip()
        
        # If all else fails
        raise ValueError("Could not extract JSON and markdown from the response")
    
    def fix_json_format(self, json_str: str) -> str:
        """Attempt to fix common JSON formatting issues."""
        # Replace single quotes with double quotes
        json_str = re.sub(r"(?<!\w)'(.*?)'(?!\w)", r'"\1"', json_str)
        
        # Fix missing quotes around keys
        json_str = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', json_str)
        
        # Fix trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        return json_str
    
    def get_gpt_recommendations(
        self, 
        rag_context: str, 
        user_query: str,
        model: str = "openai/gpt-4.1",
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Tuple[Recommendation, str]:
        """
        Get recommendations using GPT models.
        
        Args:
            rag_context: Retrieved context from vector DB
            user_query: User query with requirements
            model: GPT model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (recommendation_object, explanation_markdown)
        """
        system_prompt = {
            "role": "system",
            "content": (
                "You are an expert water-treatment design assistant. You will receive three inputs:  "
                "1) RAG-retrieved context containing technical excerpts on pumps, filters, RO membranes, "
                "and training-manual guidance. 2) A user request specifying capacity, application, and lab results.  "
                "3) A url which contains the company websites products which you must scrape in detail and find "
                "products you will pass as a recommendation in case the rag context does not contain all the products you need for the recommendation."
                "Your task is to select the optimal Reverse Osmosis unit and then specify its required pretreatment and post-treatment products, "
                "Recommend products mentioned in the context and those found at the url given\n\n"
                "The website url is : https://www.davisandshirtliff.com/products-and-solutions/"
                "Include products -like chemical dosage, chemicals, airblowers, pumps, water treatment media, filters, and type of ros to use-"
                "depending on the pretreatment and postreatment depending on the RO chosen based on the results from lab report."
                "Avoid repeating of products or giving a product dealing with a pretreatment that another product has already dealt with"
                "Just be as accurate as possible when giving results"
                "**First**, emit ONLY a JSON object matching these Pydantic schemas (no extra keys):\n\n"
                "```python\n"
                "class Product(BaseModel):\n"
                "    product_description: str\n"
                "    product_name: str\n"
                "    model_number: str\n\n"
                "class Recommendation(BaseModel):\n"
                "    pretreatment: list[Product]\n"
                "    RO:           list[Product]\n"
                "    postreatment: list[Product]\n"
                "```\n\n"
                "**Then**, in Markdown, explain your approach under these headings:\n"
                "**RO SELECTED**, **Pretreatment**, **Posttreatment**."
            )
        }
        
        user_query_content = {
            "role": "user",
            "content": f"{rag_context}\n\n{user_query}"
        }
        
        response = self.gpt_client.chat.completions.create(
            model=model,
            messages=[system_prompt, user_query_content],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        reply_text = response.choices[0].message.content.strip()
        
        # Extract JSON and markdown parts
        json_part, markdown_part = self.extract_json_and_markdown(reply_text)
        
        try:
            # Parse JSON into Pydantic model
            recommendation = Recommendation.model_validate_json(json_part)
            return recommendation, markdown_part
        except Exception as e:
            fixed_json = self.fix_json_format(json_part)
            try:
                recommendation = Recommendation.model_validate_json(fixed_json)
                return recommendation, markdown_part
            except Exception as e2:
                raise ValueError(f"Failed to parse recommendation: {e2}. JSON: {json_part}")
    
    def get_gemini_recommendations(
        self, 
        rag_context: str, 
        user_query: str,
        model: str = "gemini-2.5-pro-exp-03-25",
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Tuple[Recommendation, str]:
        """
        Get recommendations using Gemini models.
        
        Args:
            rag_context: Retrieved context from vector DB
            user_query: User query with requirements
            model: Gemini model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (recommendation_object, explanation_markdown)
        """
        system_prompt = (
            "You are an expert water-treatment design assistant. You will receive three inputs:  "
            "1) RAG-retrieved context containing technical excerpts on pumps, filters, RO membranes, "
            "and training-manual guidance. 2) A user request specifying capacity, application, and lab results.  "
            "3) A url which contains the company websites products which you must scrape in detail and find "
            "products you will pass as a recommendation in case the rag context does not contain all the products you need for the recommendation."
            "Your task is to select the optimal Reverse Osmosis unit and then specify its required pretreatment and post-treatment products, "
            "Recommend products mentioned in the context and those found at the url given\n\n"
            "The website url is : https://www.davisandshirtliff.com/products-and-solutions/"
            "Include products -like chemical dosage, chemicals, airblowers, pumps, water treatment media, filters, and type of ros to use-"
            "depending on the pretreatment and postreatment depending on the RO chosen based on the results from lab report."
            "**First**, emit ONLY a JSON object matching these Pydantic schemas (no extra keys):\n\n"
            "```python\n"
            "class Product(BaseModel):\n"
            "    product_description: str\n"
            "    product_name: str\n"
            "    model_number: str\n\n"
            "class Recommendation(BaseModel):\n"
            "    pretreatment: list[Product]\n"
            "    RO:           list[Product]\n"
            "    postreatment: list[Product]\n"
            "```\n\n"
            "**Then**, in Markdown, explain your approach under these headings:\n"
            "**RO SELECTED**, **Pretreatment**, **Posttreatment**."
        )
        
        full_prompt = f"{system_prompt}\n\n{rag_context}\n\n{user_query}"
        
        # Get response from Gemini
        try:
            response = self.gemini_client.models.generate_content(
                model=model, 
                contents=f"{full_prompt}",
            )
            reply_text = response.text
            
            # Extract JSON and markdown parts
            try:
                json_part, markdown_part = self.extract_json_and_markdown(reply_text)
                
                # Try to fix common JSON formatting issues
                json_part = self.fix_json_format(json_part)
                
                try:
                    # Parse JSON into Pydantic model
                    recommendation = Recommendation.model_validate_json(json_part)
                    return recommendation, markdown_part
                except Exception as e:
                    # Attempt a more forgiving parse as fallback
                    data = json.loads(json_part)
                    recommendation = Recommendation.model_validate(data)
                    return recommendation, markdown_part
            except ValueError:
                # Return the full response as markdown if JSON extraction fails
                return None, reply_text
                
        except Exception as e:
            raise ValueError(f"API request failed: {e}")
    
    def process(
        self, 
        user_query: str, 
        lab_report_json: str,
        model_type: str = "gpt",
        model_name: str = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Tuple[Recommendation, str]:
        """
        Process a user query and return water treatment recommendations.
        
        Args:
            user_query: User's request for treatment design
            lab_report_json: JSON string containing water lab analysis
            model_type: 'gpt' or 'gemini'
            model_name: Specific model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (recommendation_object, explanation_markdown)
        """
        # Generate search query from lab report
        search_query = self.generate_search_query(lab_report_json, user_query)
        
        # Build context from vector DB
        rag_context = self.build_context(search_query)
        
        # Select model and get recommendations
        if model_type.lower() == "gpt":
            model = model_name or "openai/gpt-4.1"
            return self.get_gpt_recommendations(
                rag_context, 
                user_query, 
                model=model,
                temperature=temperature, 
                max_tokens=max_tokens
            )
        elif model_type.lower() == "gemini":
            model = model_name or "gemini-2.5-pro-exp-03-25"
            return self.get_gemini_recommendations(
                rag_context, 
                user_query, 
                model=model,
                temperature=temperature, 
                max_tokens=max_tokens
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}. Use 'gpt' or 'gemini'.")


# Helper function to load lab report from file
def load_lab_report(file_path: str) -> str:
    """Load lab report JSON from file."""
    try:
        with open(file_path, 'r') as f:
            water_data = json.load(f)
        return json.dumps(water_data, indent=2)
    except FileNotFoundError:
        raise FileNotFoundError(f"Water analysis file not found: {file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in file: {file_path}")
