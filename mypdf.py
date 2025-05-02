import pdfplumber
import json
import os
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pdf_processor")

class PDFDataExtractor:
    """Class to handle extraction of data from PDF files"""
    
    def __init__(self, pdf_path: str):
        """Initialize with path to PDF file"""
        self.pdf_path = pdf_path
        self.raw_data = []
        self.cleaned_data = []
        
    def extract_tables(self) -> bool:
        """Extract tables from the PDF file"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        self.raw_data.extend(tables)
            
            if not self.raw_data:
                logger.warning(f"No tables found in {self.pdf_path}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error extracting tables from {self.pdf_path}: {str(e)}")
            return False
    
    def clean_data(self) -> List[List[Any]]:
        """Clean the extracted raw data and return the cleaned data"""
        self.cleaned_data = self._clean_pdf_data(self.raw_data)
        return self.cleaned_data
        
    def _clean_pdf_data(self, data: List[List[Any]]) -> List[List[Any]]:
        """Clean PDF data by removing None values and empty strings"""
        def clean_inner_list(inner_list: List[Any]) -> Optional[List[Any]]:
            # Remove None values and empty strings
            cleaned = [item for item in inner_list if item is not None and item != '']
            return cleaned if cleaned else None  # Return None if list becomes empty
        
        # Clean each inner list and remove empty results
        cleaned_data = []
        for sublist in data:
            cleaned_sublist = [clean_inner_list(inner) for inner in sublist if isinstance(inner, list)]
            cleaned_sublist = [x for x in cleaned_sublist if x]  # Remove None results
            if cleaned_sublist:  # Only add non-empty sublists
                cleaned_data.append(cleaned_sublist)
        
        return cleaned_data[0] if cleaned_data else []  # Return first sublist since input is nested in an extra layer


class WaterReportParser:
    """Parser specifically for water report PDFs"""
    
    def __init__(self, cleaned_data: List[List[Any]]):
        """Initialize with cleaned data"""
        self.cleaned_data = cleaned_data
        self.header = {}
        self.physical_analysis = []
        self.chemical_analysis = []
        self.final_comments = []
        
    def parse_header(self) -> Dict[str, Dict[str, str]]:
        """Parse header information"""
        try:
            # Ensure we have enough data rows
            if len(self.cleaned_data) < 4:
                logger.error("Not enough data to parse header")
                return {}
            
            # Check if data has expected format
            for i in range(1, 4):
                if len(self.cleaned_data[i]) < 3:
                    logger.warning(f"Header row {i} doesn't have expected format")
            
            self.header = {
                "client_info": {
                    "client": self._extract_field_value(self.cleaned_data[1][0]) if len(self.cleaned_data[1]) > 0 else "Unknown",
                    "site_location": self._extract_field_value(self.cleaned_data[2][0]) if len(self.cleaned_data[2]) > 0 else "Unknown"
                }, 
                "sample_info": {
                    "source": self._extract_field_value(self.cleaned_data[2][1]) if len(self.cleaned_data[2]) > 1 else "Unknown",
                    "reference_no": self._extract_field_value(self.cleaned_data[1][1]) if len(self.cleaned_data[1]) > 1 else "Unknown",
                    "date_received": self._extract_field_value(self.cleaned_data[1][2]) if len(self.cleaned_data[1]) > 2 else "Unknown",
                    "date_of_analysis": self._extract_field_value(self.cleaned_data[2][2]) if len(self.cleaned_data[2]) > 2 else "Unknown",
                    "type_of_test": self._extract_field_value(self.cleaned_data[3][0]) if len(self.cleaned_data[3]) > 0 else "Unknown",
                    "sampling_date": self._extract_field_value(self.cleaned_data[3][1]) if len(self.cleaned_data[3]) > 1 else "Unknown",
                    "reporting_date": self._extract_field_value(self.cleaned_data[3][2]) if len(self.cleaned_data[3]) > 2 else "Unknown"
                }
            }
            return self.header
        except Exception as e:
            logger.error(f"Error parsing header: {str(e)}")
            return {}
    
    def _extract_field_value(self, field_str: str) -> str:
        """Extract value part from a field string like 'Field: Value'"""
        try:
            return field_str.split(":", 1)[1].strip()
        except (IndexError, AttributeError):
            return "Unknown"
    
    def parse_analysis_data(self) -> Tuple[List[Dict[str, Dict[str, str]]], List[Dict[str, Dict[str, str]]], List[Dict[str, str]]]:
        """Parse analysis data into physical, chemical sections and comments"""
        try:
            all_analysis = []
            section_marker_index = None
            comments_marker_index = None
            
            # Find index positions for sections
            for i, row in enumerate(self.cleaned_data[7:], 7):
                if len(row) == 1:
                    if row[0] and 'chemical analysis' in row[0].lower():
                        section_marker_index = i
                    elif row[0] and 'comments' in row[0].lower():
                        comments_marker_index = i
            
            # Process analysis data
            current_section = "physical"
            for i, row in enumerate(self.cleaned_data[7:], 7):
                # Switch to chemical section when marker is encountered
                if section_marker_index and i == section_marker_index:
                    current_section = "chemical"
                    continue
                
                # Stop processing when comments section is reached
                if comments_marker_index and i == comments_marker_index:
                    break
                    
                # Process analysis rows (5 columns format)
                if len(row) == 5:
                    analysis_item = self._parse_analysis_row(row)
                    if analysis_item:
                        all_analysis.append(analysis_item)
            
            # Split analysis into physical and chemical sections
            if section_marker_index:
                physical_end = section_marker_index - 7  # Adjust for enumeration offset
                self.physical_analysis = all_analysis[:physical_end]
                self.chemical_analysis = all_analysis[physical_end:]
            else:
                # If no chemical section marker found, all is physical
                self.physical_analysis = all_analysis
                self.chemical_analysis = []
            
            # Parse comments if available
            if comments_marker_index:
                comment_rows = self.cleaned_data[comments_marker_index+1:comments_marker_index+4]
                metadata_row = self.cleaned_data[comments_marker_index+4] if comments_marker_index+4 < len(self.cleaned_data) else []
                
                comments = ' '.join(' '.join(item) for item in comment_rows if item)
                metadata = ' '.join(metadata_row) if metadata_row else ""
                
                self.final_comments = [{
                    "comments": comments,
                    "signof": metadata
                }]
            
            return self.physical_analysis, self.chemical_analysis, self.final_comments
        except Exception as e:
            logger.error(f"Error parsing analysis data: {str(e)}")
            return [], [], []
    
    def _parse_analysis_row(self, row: List[str]) -> Optional[Dict[str, Dict[str, str]]]:
        """Parse a single analysis row"""
        try:
            parameter = row[0]
            method = row[1]
            unit = row[2]
            value = row[3]
            guideline = row[4]
            
            # Determine remark based on value and guideline
            remark = "None"
            
            if guideline == 'NS':
                remark = "None"
            elif guideline == 'NIL':
                try:
                    remark = "Pass" if float(value) == 0 else "Fail"
                except ValueError:
                    remark = "Unknown"
            elif '-' in guideline:  # Range format like '6.5 - 8.50'
                try:
                    range_values = guideline.split('-')
                    min_value = float(range_values[0].strip())
                    max_value = float(range_values[1].strip())
                    remark = "Pass" if min_value <= float(value) <= max_value else "Fail"
                except ValueError:
                    remark = "Unknown"
            elif '<' in guideline:  # Less than format like '<1000'
                try:
                    limit_value = float(guideline.replace('<', '').strip())
                    remark = "Pass" if float(value) < limit_value else "Fail"
                except ValueError:
                    remark = "Unknown"
            
            return {
                parameter: {
                    "method_of_analysis": method,
                    "unit": unit,
                    "value": value,
                    "who_guideline": guideline,
                    "remark": remark
                }
            }
        except Exception as e:
            logger.warning(f"Error parsing analysis row {row}: {str(e)}")
            return None

    def get_full_results(self) -> Dict[str, Any]:
        """Get the complete structured results"""
        return {
            "header": self.header,
            "physical_analysis": self.physical_analysis,
            "chemical_analysis": self.chemical_analysis,
            "final_comments": self.final_comments
        }


# Module-level functions for ease of use
def extract_pdf_data(pdf_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract and process data from a water report PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path to save the JSON output
    
    Returns:
        Dict containing the structured data extracted from the PDF
    """
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Generate output path if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = f"outputs/{base_name}_output.json"
    else:
        output_path = 'outputs/' + output_path
    
    # Extract and clean data
    extractor = PDFDataExtractor(pdf_path)
    if not extractor.extract_tables():
        logger.error(f"Failed to extract tables from {pdf_path}")
        return {}
        
    cleaned_data = extractor.clean_data()
    
    # Parse data
    parser = WaterReportParser(cleaned_data)
    header = parser.parse_header()
    physical_analysis, chemical_analysis, final_comments = parser.parse_analysis_data()
    
    # Combine results
    result = {
        "header": header,
        "physical_analysis": physical_analysis,
        "chemical_analysis": chemical_analysis,
        "final_comments": final_comments,
        "metadata": {
            "processed_date": datetime.now().isoformat(),
            "source_file": os.path.basename(pdf_path)
        }
    }
    # Save to file
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=4)
        logger.info(f"Data saved to {output_path}")
    
    return result


def batch_process_pdfs(input_dir: str, output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Process all PDF files in a directory.
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Optional directory to save JSON outputs
    
    Returns:
        List of dictionaries containing structured data from each PDF
    """
    # Create output directory if specified and it doesn't exist
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return []
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    results = []
    
    for pdf_file in pdf_files:
        input_path = os.path.join(input_dir, pdf_file)
        
        # Generate output path if output directory is specified
        output_path = None
        if output_dir:
            base_name = os.path.splitext(pdf_file)[0]
            output_path = os.path.join(output_dir, f"{base_name}_output.json")
        
        try:
            result = extract_pdf_data(input_path, output_path)
            results.append(result)
            logger.info(f"Successfully processed {pdf_file}")
        except Exception as e:
            logger.error(f"Error processing {pdf_file}: {str(e)}")
    
    return results

