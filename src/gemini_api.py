"""
Gemini API integration for architectural data extraction.
"""

import gc
import os
import json
import re
import time
from typing import Dict, List, Optional, Tuple
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
        self, image: Image.Image, extraction_fields: List[str], page_num: int = 1,
        page_text: str = "", title_block_crop: Optional[Image.Image] = None
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
                # Hybrid injection: prepend machine-readable text extracted by PyMuPDF
                hybrid_context = ""
                if page_text and page_text.strip():
                    hybrid_context = (
                        f"\n\n=== MACHINE-READABLE TEXT EXTRACTED BY PyMuPDF (Page {page_num}) ===\n"
                        f"{page_text.strip()}\n"
                        "=== END EXTRACTED TEXT ===\n"
                        "IMPORTANT: The text above was extracted directly from the PDF's embedded data "
                        "(not OCR). Treat dimension values, area figures, and labels found in this text "
                        "as HIGH-CONFIDENCE ground truth. Use the image to fill any gaps not covered "
                        "by the extracted text.\n"
                    )

                contents = [system_prompt, image]

                # Super Skill 3: inject the title block crop when available so
                # Gemini receives a zoomed close-up of the region that contains
                # project name, scale, drawing number, date, etc.
                if title_block_crop is not None:
                    contents.append(
                        "The image below is a zoomed high-resolution crop of the "
                        "TITLE BLOCK region of this page. Use it to extract "
                        "project metadata fields (scale, drawing number, date, "
                        "client, etc.) with higher precision:"
                    )
                    contents.append(title_block_crop)

                contents.append(
                    f"\n\nIMPORTANT: You are currently analyzing PAGE {page_num} of the original PDF. "
                    f"In your reasoning and page_reference fields, you MUST write 'Page {page_num}'.\n"
                    + hybrid_context
                    + "\nPlease extract the requested data and return results as JSON."
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
                print(f"=== EXCEPTION on page {page_num} attempt {attempt + 1}/{max_retries} ===")
                print(f"  Type : {type(e).__name__}")
                print(f"  Error: {error_str}")
                import traceback as _tb; _tb.print_exc()
                print(f"=== END EXCEPTION ===")

                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Daily quota exhaustion cannot be fixed by retrying — fail immediately
                    if "PerDay" in error_str or "per_day" in error_str:
                        raise RuntimeError(
                            f"Daily API quota exhausted (free tier limit reached). "
                            f"Please wait until tomorrow or upgrade your Gemini API plan. "
                            f"Details: {error_str[:300]}"
                        )
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit for page {page_num} (attempt {attempt + 1}/{max_retries}), will retry...")
                        continue
                    else:
                        raise RuntimeError(f"Rate limit error for page {page_num} after {max_retries} attempts: {error_str}")
                else:
                    # Non-rate-limit error: raise immediately, no further retries
                    raise RuntimeError(f"[{type(e).__name__}] Error on page {page_num}: {error_str}")
        
        # This should never be reached, but just in case
        raise RuntimeError(f"Failed to process page {page_num} after {max_retries} attempts")

    def extract_data_from_multiple_pages(
        self,
        page_iterator,
        extraction_fields: List[str],
        progress_callback=None,
        total_pages: int = 0,
        checkpoint_callback=None,
    ) -> Tuple[Dict[str, Dict[str, any]], Optional[str]]:
        """
        Extract data lazily, one page at a time, to minimise peak memory usage.

        Accepts an iterable of (PIL.Image, page_text) tuples — typically from
        PDFProcessor.iter_pages(). After each page is processed the image
        reference is explicitly deleted and gc.collect() is called so memory
        is freed before the next page is loaded.

        Smart Merge: a running master_dict is maintained across pages. After
        each page, each field is updated in master_dict ONLY if the new
        confidence score is strictly higher than the currently stored value for
        that field. This ensures the best extraction from ANY page wins.

        If the Google API daily quota is exhausted mid-run, processing stops
        immediately and partial results gathered so far are returned rather
        than crashing the application.

        Args:
            page_iterator: Iterable of (PIL.Image, page_text_str, title_block_crop)
                tuples — typically from PDFProcessor.iter_pages().
                title_block_crop is a PIL Image or None.
            extraction_fields: List of field codes to extract
            progress_callback: Optional callback(page_num, total_pages)
            total_pages: Total page count for progress / rate-limit logic
            checkpoint_callback: Optional callable(page_num, master_dict).
                Called after every successful page so callers can persist
                incremental data (e.g. write to Supabase) before the next page.

        Returns:
            Tuple of (master_dict, quota_warning_str_or_None).
            quota_warning_str is None when no quota issues occurred.
        """
        print(f"Processing {total_pages} pages lazily (one at a time) with rate limiting...")

        # master_dict holds the running best-confidence result per field across pages
        master_dict: Dict[str, Dict] = {}
        pages_processed = 0
        failed_pages = []
        quota_warning = None
        page_num = 0

        for image, page_text, title_block_crop in page_iterator:
            page_num += 1
            try:
                print(f"Processing page {page_num}/{total_pages}...")
                page_result = self.extract_data_from_image(
                    image, extraction_fields, page_num, page_text,
                    title_block_crop=title_block_crop,
                )

                # ── Smart Merge: best-confidence-wins per field ──────────────
                # Iterate over this page's results and update master_dict only
                # when the new confidence is strictly higher than what we have.
                for field_code, field_data in page_result.items():
                    if not isinstance(field_data, dict):
                        continue
                    new_conf = field_data.get("confidence", 0)
                    if field_code not in master_dict:
                        master_dict[field_code] = field_data
                    elif new_conf > master_dict[field_code].get("confidence", 0):
                        master_dict[field_code] = field_data

                pages_processed += 1
                print(f"Page {page_num} done — master_dict now has {len(master_dict)} fields.")

                # Progress callback wrapped so UI errors can't kill the loop
                if progress_callback:
                    try:
                        progress_callback(page_num, total_pages)
                    except Exception as prog_err:
                        print(f"Progress callback warning (non-fatal): {prog_err}")

                # Incremental checkpoint: persist the best-so-far master_dict to Supabase
                if checkpoint_callback and master_dict:
                    try:
                        checkpoint_callback(page_num, master_dict)
                    except Exception as ckpt_err:
                        print(f"Checkpoint callback warning (non-fatal): {ckpt_err}")

                # Rate limiting: 15s between pages (never after the last page)
                if total_pages > 0 and page_num < total_pages:
                    print(f"Waiting 15s before page {page_num + 1}/{total_pages}...")
                    time.sleep(15)

            except RuntimeError as e:
                error_msg = str(e)
                print(f"Page {page_num} FAILED: {error_msg}")

                if "Daily API quota exhausted" in error_msg:
                    # Daily quota cannot be recovered by retrying — stop now and
                    # return whatever partial data was collected before the limit.
                    quota_warning = (
                        f"Google API daily quota exhausted after page {page_num - 1}. "
                        f"Partial results from {pages_processed} successfully extracted "
                        "page(s) are shown. Please wait until tomorrow or upgrade your "
                        "Gemini API plan."
                    )
                    print(f"Daily quota hit — stopping with {pages_processed} partial result(s).")
                    break  # Only valid early exit — daily quota cannot recover

                failed_pages.append((page_num, error_msg))
                # Apply rate-limit delay on non-quota failures too
                if total_pages > 0 and page_num < total_pages:
                    time.sleep(15)

            finally:
                # Explicit memory release after each page regardless of outcome
                del image
                if title_block_crop is not None:
                    del title_block_crop
                gc.collect()

        # Close the generator explicitly so fitz doc is released promptly
        if hasattr(page_iterator, "close"):
            page_iterator.close()

        # If nothing succeeded at all, raise so the UI shows a clear error
        if not master_dict:
            if quota_warning:
                raise RuntimeError(quota_warning)
            first_error = failed_pages[0][1] if failed_pages else "Unknown error"
            raise RuntimeError(
                f"All {total_pages} pages failed to extract. First error: {first_error}"
            )

        if failed_pages:
            print(f"Warning: {len(failed_pages)}/{total_pages} pages failed: "
                  f"{[p for p, _ in failed_pages]}")

        print(f"Extraction complete: {pages_processed}/{total_pages} pages succeeded, "
              f"{len(master_dict)} fields in master_dict.")
        return master_dict, quota_warning

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
        fields_count = len(extraction_fields)

        return f"""You are a PROFESSIONAL architectural plan analyzer and construction estimating expert with deep knowledge of building codes, residential construction standards, and plan documentation conventions.

================================================================================
HYBRID EXTRACTION INSTRUCTIONS
================================================================================

When machine-readable text extracted by PyMuPDF is provided alongside the image,
you MUST treat that text as primary HIGH-CONFIDENCE source data. Cross-reference it
with the visual image. The image is used to fill in values not captured in text.

================================================================================
ARCHITECTURAL GLOSSARY (use to interpret field codes correctly)
================================================================================

FOUNDATIONS:
  SL_TOTAL/SL_HS/SL_GAR/SL_POR — concrete slab square footage for each area
  FND_FTG — perimeter footings in linear feet; FND_FTG_PAD — isolated pad footings

WALLS:
  WE_* — Exterior walls by stud size (2x4, 2x6) or material (CMU block)
  WI_* — Interior partition walls; WI_MTL = light gauge metal stud
  WE_TOTAL/WI_TOTAL — sum of all exterior/interior wall segments in LF

SHEATHING: OSB or plywood panels applied to walls, floor, and roof decks
  SH_WA_FIRE / SH_RF_FIRE — Type-X fire-rated gypsum or rated sheathing

ROOFING GEOMETRY:
  RF_EV = eave (horizontal overhang edge); RF_HP = hip rafter line
  RF_RK = rake (sloped gable edge); RF_RDG = ridge cap; RF_VL = valley (interior intersection)
  RF_RKW = rake meets a wall; RF_EVW = eave meets a wall; RF_RDGV = ridge vent strip

SIDING / EXTERIOR FINISHES:
  EF_HS = horizontal lap siding; EF_BNB = board-and-batten vertical siding
  EF_SHK = shake/shingle siding; EF_STN = stone veneer; EF_BRI = brick veneer
  Soldier course = brick/stone laid vertically on end (above windows)
  Rowlock course = brick laid on edge with hole visible (window sill detail)
  Watertable = decorative horizontal band at base of wall, typically different material

LINTELS: steel angles or precast concrete beams spanning door/window openings

TRIMS:
  TE_CNR = corner trim boards; TE_SHR = shutters (decorative or functional)
  TE_SOFFIT = underside of roof overhang cladding; TE_FASCIA = vertical trim at eave edge
  TE_ZFLASH = Z-shaped metal flashing at horizontal joints; TE_FOAM = decorative foam trim
  TE_DS = downspouts; TE_GUTTER = gutters at eave

DOORS: DI_SW = single-swing interior; DI_2SW = double-swing (French doors)
  LF_DOOR_CASING = linear feet of door casing trim; INT_CASING = count of cased openings

================================================================================
PROFESSIONAL ACCURACY LEVEL - ANALYSIS REQUIREMENTS
================================================================================

YOUR TASK:
Analyze ALL {total_pages} architectural PDF pages and extract data using the Generic Key Measures standard ({fields_count} fields across 15 categories). Provide PROFESSIONAL-GRADE analysis with full traceability, validation, and reasoning.

CRITICAL PROFESSIONAL REQUIREMENTS:

1. SCALE IDENTIFICATION FIRST: Before ANY linear measurements, identify the drawing scale on each page. Document this in your reasoning.

2. HYBRID TEXT PRIORITY: If PyMuPDF-extracted text is present, read it FIRST and populate fields directly from it before consulting the image.

3. TRACEABILITY & REASONING: For EVERY extracted value, provide detailed reasoning explaining:
   - Which page(s) the data was found on
   - Whether value came from embedded text (PyMuPDF) or visual interpretation
   - How the value was determined

4. VALIDATION: If you calculate a value that contradicts a printed dimension, flag it.

5. SANITY CHECKS: After extracting all data, perform these sanity checks:
   - Does SL_TOTAL = SL_HS + SL_GAR + SL_POR? (if components present)
   - Is WE_TOTAL approximately 2×(WIDTH_FT + DEPTH_FT)?
   - Do WIN_TOTAL = WIN_SINGLE + WIN_DOUBLE? Do DOOR_TOTAL = DOOR_EXT + DOOR_INT?

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
