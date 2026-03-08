# Architectural PDF Data Extractor

A Streamlit web application that extracts structured data from architectural PDF plans using Google's Gemini 1.5 Pro API with high-resolution visual capabilities.

## Features

✅ **PDF Processing**: Converts PDF pages to high-resolution images (300+ DPI)
✅ **AI-Powered Extraction**: Uses Gemini 1.5 Pro for intelligent data recognition
✅ **Dynamic Categories**: Easily configurable extraction fields and categories
✅ **Confidence Scoring**: Each extracted value includes a 0-100% confidence level
✅ **Multi-Page Support**: Aggregates results from multiple PDF pages
✅ **Export Options**: Download results as CSV or JSON

## Data Extraction

### General Information
- Plan Number
- Elevation
- Stories
- Width (FT)
- Depth (FT)
- Bathrooms
- Bedrooms

### Key Measurements
- Concrete Slab Area (SF)
- Exterior Wall Linear (LF)
- Interior Wall Linear (LF)
- Window Count
- Door Count

## Project Structure

```
├── app.py                          # Main Streamlit application
├── config/
│   └── extraction_categories.py   # Dynamic category configuration
├── src/
│   ├── pdf_processor.py           # PDF to image conversion
│   └── gemini_api.py              # Gemini API integration
├── data/
│   └── generic_key_measures.csv   # Reference CSV for measurements
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## Installation & Setup

### 1. Clone/Setup Project

```bash
cd /Users/stavhurgin/Documents/Arch\ Extract
```

### 2. Install System Dependencies

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
apt-get install poppler-utils
```

**Windows:**
Download from [poppler-windows releases](https://github.com/oschwartz10612/poppler-windows/releases/)

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Gemini API

- Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Copy `.env.example` to `.env`:
  ```bash
  cp .env.example .env
  ```
- Add your Gemini API key to `.env`:
  ```
  GEMINI_API_KEY=your_actual_api_key_here
  ```

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Usage

1. **Upload PDF**: Select an architectural PDF file
2. **Select Categories**: Choose which data categories to extract
3. **Extract Data**: Click "Extract Data" to process
4. **Review Results**: Check the extracted data and confidence levels
5. **Export**: Download results as CSV or JSON

## Configuration

### Adding New Extraction Categories

Edit `config/extraction_categories.py`:

```python
EXTRACTION_CATEGORIES = {
    "your_category": {
        "label": "Display Name",
        "fields": [
            {"name": "field_name", "display": "Field Display Name", "uom": "Unit"},
            # Add more fields...
        ],
    },
}
```

### Adjusting PDF Processing

In `src/pdf_processor.py`, modify the `PDFProcessor` initialization:
- `dpi`: Resolution (default: 300, range: 150-600)
- `fmt`: Image format (default: "png")

## System Prompts

The extraction system uses carefully crafted prompts sent to Gemini that:
- Define precise extraction requirements
- Specify response formats
- Include guidelines for measurement accuracy
- Provide confidence scoring thresholds

Prompts are in `src/gemini_api.py::_build_system_prompt()`

## Dependencies

- **streamlit**: Web UI framework
- **google-generativeai**: Gemini API client
- **pdf2image**: PDF to image conversion
- **pillow**: Image processing
- **pandas**: Data manipulation
- **python-dotenv**: Environment variable management

## Environment Requirements

- Python 3.8+
- macOS/Linux/Windows
- Poppler (required for pdf2image)
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`
  - Windows: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)

## Troubleshooting

### API Key Issues
```
If you get "GEMINI_API_KEY not found", ensure:
1. .env file exists in project root
2. GEMINI_API_KEY is properly set
3. Environment is sourced correctly
```

### PDF Conversion Errors
```
If pdf2image fails:
1. Verify Poppler is installed
2. macOS: brew install poppler
3. Check PDF is not corrupted
```

### Memory / Large Files
```
For large PDFs:
1. Reduce DPI setting in sidebar (try 150-200)
2. Process one page at a time if needed
3. Ensure sufficient RAM available
```

## Future Enhancements

- [ ] Batch processing for multiple PDFs
- [ ] Template-based extraction for consistency
- [ ] OCR capability for text recognition
- [ ] Result validation and correction UI
- [ ] Database integration for result storage
- [ ] Email delivery of results
- [ ] Custom field definitions per project
- [ ] Before/after image comparison

## API Costs

Usage of Gemini 1.5 Pro API may incur charges based on:
- Image tokens (resolution and number of pages)
- Input/output tokens (data extraction complexity)

Check [Google AI Pricing](https://ai.google.dev/pricing) for current rates.

## License

[Add your license here]

## Support

For issues or questions, please refer to:
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [PDF2Image Documentation](https://github.com/Belval/pdf2image)
