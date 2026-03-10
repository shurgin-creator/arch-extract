"""
Gemini API integration for architectural data extraction.
"""

import os
import json
import time
from typing import Dict, List, Optional
from PIL import Image
import google.genai as genai


class GeminiDataExtractor:
    """Handles interaction with Gemini API for data extraction."""

    def __init__(self, api_key: Optional[str] = None, model: str = "models/gemini-flash-latest"):
        """
        Initialize Gemini API client.

        Args:
            api_key: Gemini API key (uses env var if not provided)
            model: Model identifier (default: models/gemini-flash-latest)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables or arguments")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model
        
        # list available models for debugging
        try:
            models = self.client.models.list()
            print("=== AVAILABLE GEMINI MODELS ===")
            for m in models:
                if 'gemini' in m.name.lower():
                    print(f"- {m.name}")
            print("=== END MODEL LIST ===")
        except Exception as e:
            print(f"Could not list models: {e}")

    def extract_data_from_image(
        self, image: Image.Image, extraction_fields: List[str], page_num: int = 1
    ) -> Dict[str, Dict[str, any]]:
        """
        Extract architectural data from a single image using Gemini.
        Includes exponential backoff retry logic for rate limiting errors.

        Args:
            image: PIL Image of PDF page
            extraction_fields: List of field names to extract
            page_num: Page number for reference

        Returns:
            Dictionary with extracted data and confidence levels
        """
        system_prompt = self._build_consolidated_system_prompt(extraction_fields, 1)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Calculate exponential backoff delay for retries
                if attempt > 0:
                    delay = 10 * (2 ** (attempt - 1))  # 10s, 20s, 40s
                    print(f"Retry attempt {attempt} for page {page_num}, waiting {delay}s...")
                    time.sleep(delay)
                
                # Generate content using new google.genai API
                contents = [
                    system_prompt,
                    image,
                    "\n\nPlease analyze this architectural PDF page and extract the requested data. "
                    "Return results as JSON with field_name, value, unit, and confidence (0-100) for each field."
                ]
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )

                # Parse the response
                extracted_data = self._parse_response(response, extraction_fields)
                return extracted_data

            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        # Don't wait here - exponential backoff is handled at the start of next attempt
                        print(f"Rate limit hit for page {page_num} (attempt {attempt + 1}/{max_retries})")
                        continue
                    else:
                        print(f"Rate limit error persisted for page {page_num} after {max_retries} attempts. Skipping page.")
                        raise RuntimeError(f"Rate limit error for page {page_num}: {error_str}")
                else:
                    # Non-rate-limit error, don't retry
                    raise RuntimeError(f"Error extracting data from image using Gemini: {error_str}")
        
        # This should never be reached, but just in case
        raise RuntimeError(f"Failed to process page {page_num} after {max_retries} attempts")

    def extract_data_from_multiple_pages(
        self, images: List[Image.Image], extraction_fields: List[str], progress_callback=None
    ) -> Dict[str, Dict[str, any]]:
        """
        Extract data from ALL PDF pages and aggregate results.
        Processes every single page of the PDF with rate limiting to avoid API quota issues.
        
        Args:
            images: List of PIL Images
            extraction_fields: List of field names to extract
            progress_callback: Optional callback function to update progress (page_num, total_pages)
            
        Returns:
            Aggregated extraction results
        """
        total_pages = len(images)
        print(f"Processing ALL {total_pages} pages of the PDF with rate limiting...")
        
        all_results = []
        
        for page_num, image in enumerate(images, 1):
            try:
                print(f"Processing page {page_num}/{total_pages}...")
                result = self.extract_data_from_image(image, extraction_fields, page_num)
                result["page_number"] = page_num
                all_results.append(result)
                
                # Update progress if callback provided
                if progress_callback:
                    progress_callback(page_num, total_pages)
                
                # Rate limiting: wait 15 seconds between pages (except for the last page)
                if page_num < total_pages:
                    print(f"Page {page_num}/{total_pages} - Success - Waiting 15s...")
                    time.sleep(15)
                    
            except Exception as e:
                print(f"Error processing page {page_num}: {str(e)}")
                continue
        
        # Aggregate results (take highest confidence values)
        aggregated = self._aggregate_results(all_results)
        return aggregated

    def refine_field_value(
        self, images: List[Image.Image], field_code: str, original_value: str, 
        user_feedback: str, original_reasoning: str
    ) -> Dict[str, any]:
        """
        Re-analyze a specific field based on user feedback (Challenge mechanism).
        Uses the original analysis context plus user feedback to provide a refined value.

        Args:
            images: List of PIL Images from all PDF pages
            field_code: The field code that needs refinement
            original_value: The original extracted value
            user_feedback: User's feedback/explanation of what's wrong
            original_reasoning: The original AI reasoning for this field

        Returns:
            Refined field data with new value, confidence, and reasoning
        """
        print(f"Refining field {field_code} with user feedback: {user_feedback}")

        refinement_prompt = f"""You are a professional architectural plan analyzer. 
A user has challenged an extraction result and provided feedback for improvement.

CHALLENGED FIELD: {field_code}
ORIGINAL EXTRACTED VALUE: {original_value}
ORIGINAL AI REASONING: {original_reasoning}

USER FEEDBACK/CHALLENGE: {user_feedback}

Please re-analyze the provided architectural PDF pages with this feedback in mind. 
Focus specifically on the {field_code} field and provide:

1. A NEW extracted value (or keep the original if the user is mistaken)
2. UPDATED reasoning explaining the user's feedback
3. Updated confidence level (0-100)
4. Validation status (verified, calculated_conflict, inferred, etc.)
5. Page reference where the corrected data was found

Return ONLY a JSON object with this structure:
{{
    "code": "{field_code}",
    "measure_name": "Field Name",
    "value": "NEW_VALUE",
    "unit": "UOM",
    "confidence": 85,
    "reasoning": "Detailed explanation of refinement and why it changed or didn't change",
    "validation_status": "verified",
    "page_reference": "Page X",
    "refinement_note": "Summary of what the user feedback revealed"
}}"""

        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Calculate exponential backoff delay for retries
                if attempt > 0:
                    delay = 10 * (2 ** (attempt - 1))
                    print(f"Refinement retry attempt {attempt}, waiting {delay}s...")
                    time.sleep(delay)

                # Prepare contents with refinement prompt and all images
                contents = [refinement_prompt]

                # Add all images to the contents
                for i, image in enumerate(images, 1):
                    contents.append(f"\n--- PAGE {i} ---\n")
                    contents.append(image)

                contents.append(
                    "\n\nPlease re-analyze ALL pages above with the user feedback in mind and return the refined JSON."
                )

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )

                # Parse the response
                response_text = response.text
                print(f"=== REFINEMENT RESPONSE ===\n{response_text[:500]}\n===")

                # Extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    json_str = json_match.group(0)
                    refined_field = json.loads(json_str)
                    print(f"Successfully refined field {field_code}")
                    return refined_field
                else:
                    raise ValueError("No JSON found in refinement response")

            except Exception as e:
                error_str = str(e)

                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit during refinement (attempt {attempt + 1}/{max_retries})")
                        continue
                    else:
                        raise RuntimeError(f"Rate limit error during refinement: {error_str}")
                else:
                    raise RuntimeError(f"Error refining field using Gemini: {error_str}")

        raise RuntimeError(f"Failed to refine field {field_code} after {max_retries} attempts")

    def extract_data_from_all_pages_consolidated(
        self, images: List[Image.Image], extraction_fields: List[str]
    ) -> Dict[str, Dict[str, any]]:
        """
        Extract data from ALL PDF pages in a single consolidated API call.
        Gemini analyzes all pages together and produces one comprehensive result.
        
        Args:
            images: List of PIL Images from all PDF pages
            extraction_fields: List of field names to extract
            
        Returns:
            Consolidated extraction results from all pages
        """
        total_pages = len(images)
        print(f"Sending ALL {total_pages} pages to Gemini for consolidated analysis...")
        
        system_prompt = self._build_consolidated_system_prompt(extraction_fields, total_pages)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Calculate exponential backoff delay for retries
                if attempt > 0:
                    delay = 10 * (2 ** (attempt - 1))  # 10s, 20s, 40s
                    print(f"Consolidated retry attempt {attempt}, waiting {delay}s...")
                    time.sleep(delay)
                
                # Prepare contents with system prompt and all images
                contents = [system_prompt]
                
                # Add all images to the contents
                for i, image in enumerate(images, 1):
                    contents.append(f"\n--- PAGE {i} ---\n")
                    contents.append(image)
                
                contents.append(
                    "\n\nPlease analyze ALL the architectural PDF pages above and extract the requested data. "
                    "Consolidate findings from all pages into a single comprehensive JSON result that matches the Generic Key Measures structure."
                )
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )

                # Parse the response
                extracted_data = self._parse_response(response, extraction_fields)
                return extracted_data

            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit for consolidated extraction (attempt {attempt + 1}/{max_retries})")
                        continue
                    else:
                        print(f"Rate limit error persisted for consolidated extraction after {max_retries} attempts.")
                        raise RuntimeError(f"Rate limit error for consolidated extraction: {error_str}")
                else:
                    # Non-rate-limit error, don't retry
                    raise RuntimeError(f"Error in consolidated extraction using Gemini: {error_str}")
        
        # This should never be reached, but just in case
        raise RuntimeError(f"Failed consolidated extraction after {max_retries} attempts")

   def _build_consolidated_system_prompt(self, extraction_fields: List[str], total_pages: int) -> str:
        """
        Build a professional-grade system prompt for consolidated analysis of all PDF pages.
        Includes AI reasoning, scaling validation, self-correction, and traceability.
        """
        fields_list = "\n".join([f"- {field}" for field in extraction_fields])

        return f"""You are a PROFESSIONAL architectural plan analyzer and data extraction expert with deep knowledge of building codes, standards, and construction documentation.

================================================================================
PROFESSIONAL ACCURACY LEVEL - ANALYSIS REQUIREMENTS
================================================================================

YOUR TASK:
Analyze ALL {total_pages} architectural PDF pages together and extract data using the Generic Key Measures standard. Provide PROFESSIONAL-GRADE analysis with full traceability, validation, and reasoning.

CRITICAL PROFESSIONAL REQUIREMENTS:

1. SCALE IDENTIFICATION FIRST: Before ANY linear measurements, identify the drawing scale on each page. Document this in your reasoning.

2. TRACEABILITY & REASONING: For EVERY extracted value, provide detailed reasoning explaining:
   - Which page(s) the data was found on
   - Exact location on the page
   - How the value was determined

3. VALIDATION: If you calculate a value that contradicts a printed dimension, flag it.

4. SANITY CHECKS: After extracting all data, perform these sanity checks:
   - Does SL_TOTAL = SL_HS + SL_GAR? (if both present)
   - Is EW_LF approximately 2×(WIDTH + DEPTH)?
   - Do window/door totals match their components?

================================================================================
FIELDS TO EXTRACT:
{fields_list}

================================================================================
PROFESSIONAL CONFIDENCE SCORING
================================================================================

95-100%: Data directly read from printed dimensions or clearly marked codes
80-94%:  Data calculated from clear dimensions using identified scale
60-79%:  Data inferred from partial information or standard practices
40-59%:  Data estimated or requires significant interpretation
0-39%:   Data cannot be reliably determined from visible plans
0%:      Data not present in provided image (return null)

================================================================================
PROFESSIONAL RESPONSE FORMAT
================================================================================

Return ONLY valid JSON. No preamble. No explanations. Only JSON.

Map field names/codes to this ENHANCED structure:

{{
    "extracted_fields": {{
        "PLAN_NO": {{
            "code": "PLAN_NO",
            "measure_name": "Plan Number",
            "value": "A-101",
            "unit": "",
            "confidence": 95,
            "category": "General",
            "reasoning": "Found on Page 1, Title Block, clearly printed as plan identifier",
            "validation_status": "verified",
            "page_reference": "Page 1"
        }}
    }}
}}

PROFESSIONAL VALIDATION STATUS CODES (Must be one of these):
- "verified": Data directly read from plans with high confidence
- "calculated_valid": Calculated value that validates against other measurements
- "calculated_conflict": Calculated value contradicts printed dimension
- "sanity_check_failed": Self-correction found inconsistency
- "scale_uncertain": Scale not clearly identified (may affect accuracy)
- "inferred": Data inferred from partial information
- "not_found": Data not present in provided pages

CRITICAL REQUIREMENTS:
- Use standardized codes
- ONLY return JSON—no other text
- CONSOLIDATE from ALL {total_pages} pages into ONE professional-grade result"""

    def _parse_response(self, response, extraction_fields: List[str]) -> Dict[str, Dict[str, any]]:
        """
        Parse Gemini API response and extract structured data.

        Args:
            response: Gemini API response object
            extraction_fields: Expected field names

        Returns:
            Parsed extraction results
        """
        try:
            # Extract text from response
            response_text = response.text

            # Debug: Print raw response
            print("=== RAW GEMINI RESPONSE ===")
            print(response_text[:1000])  # First 1000 chars
            print("=== END RAW RESPONSE ===")

            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                print(f"Extracted JSON string length: {len(json_str)}")
                data = json.loads(json_str)
                print(f"Parsed JSON keys: {list(data.keys())}")

                extracted_fields = data.get("extracted_fields", {})
                print(f"Extracted fields count: {len(extracted_fields)}")
                print(f"Extracted field keys: {list(extracted_fields.keys())}")

                return extracted_fields
            else:
                print("No JSON found in response!")
                raise ValueError("No JSON found in response")

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            print(f"Problematic JSON string: {json_str[:500] if 'json_str' in locals() else 'N/A'}")
            raise RuntimeError(f"Error parsing Gemini response as JSON: {str(e)}")
        except Exception as e:
            print(f"General parsing error: {str(e)}")
            raise RuntimeError(f"Error processing Gemini response: {str(e)}")

    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Dict[str, any]]:
        """
        Aggregate extraction results from multiple pages.
        Takes highest confidence values for each field.

        Args:
            results: List of extraction results from each page

        Returns:
            Aggregated results
        """
        aggregated = {}

        for result in results:
            if "extracted_fields" in result:
                fields = result["extracted_fields"]
            else:
                fields = result

            for field_name, field_data in fields.items():
                if field_name not in aggregated:
                    aggregated[field_name] = field_data
                else:
                    # Keep the value with higher confidence
                    if isinstance(field_data, dict) and isinstance(aggregated[field_name], dict):
                        if field_data.get("confidence", 0) > aggregated[field_name].get("confidence", 0):
                            aggregated[field_name] = field_data

        return aggregated
