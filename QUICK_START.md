# Quick Start Guide - Professional Features

## Getting Started

### 1. Launch the App

```bash
cd ~/Documents/Arch Extract
source venv/bin/activate
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 2. Project History (Sidebar)

When you open the app, you'll see:

```
📁 Project History
├── 📄 Floor Plan A (2026-03-08 | 5 pages) [🗑️]
├── 📄 Foundation Plan B (2026-03-07 | 3 pages) [🗑️]
└── 📄 Roof Layout C (2026-03-06 | 2 pages) [🗑️]
```

**Actions:**
- Click any project to instantly load it
- Click 🗑️ to permanently delete

---

## 3. Extract New PDF

1. **Upload**: Drag & drop or select a PDF file
2. **Configure**:
   - Choose extraction categories (left sidebar)
   - Set DPI (default: 200 is good for most PDFs)
3. **Extract**: Click "Extract Data" button
4. **Wait**: Watch the live log updates as Gemini analyzes your PDF
5. **Auto-Save**: Project automatically saved to database

---

## 4. Review Results

### The Results Table Shows:

| Column | What It Means |
|--------|--------------|
| **Code** | Standardized code (e.g., SL_HS, EW_LF) |
| **Category** | General, Measurements, or Other |
| **Key Measure** | Human-readable field name |
| **Value** | The extracted value |
| **Unit** | SF, LF, FT, etc. |
| **Confidence Level** | Color-coded: 🟢 Green=High, 🟡 Yellow=Medium, 🔴 Red=Low |
| **AI Reasoning / Source** | WHERE & HOW the AI found this data |
| **Validation Status** | Verified, Calculated, Conflicting, etc. |
| **Page Reference** | Which page(s) data came from |

### Key Sections:

**📈 Extraction Summary**
- Total fields extracted
- Number of fields with values
- Average confidence level
- Pages processed

**⚠️ Validation Issues**
- Any conflicts detected (calculated value vs. printed dimension)
- Sanity check failures (e.g., totals don't match)
- Scale uncertainty warnings

**⚠️ Low Confidence Items**
- Fields with < 70% confidence
- Usually need manual verification

---

## 5. Refine an Incorrect Extraction (Challenge Mechanism)

Found an error the AI made? Fix it:

1. **Scroll to**: "🔧 Refine Results (Challenge Mechanism)" section
2. **Select Field**: Choose the field to refine from dropdown
3. **Click**: "🔍 Refine This Field"
4. **Review Current Data**:
   - Current value and confidence
   - Complete AI reasoning
5. **Provide Feedback**: Type your correction detail
   - Example: "Width should be 50 feet. I can see '50'-0\"' clearly on page 2."
6. **Click**: "✅ Submit Refinement"
7. **Wait**: AI re-analyzes just that field (30-60 seconds)
8. **See Results**: New value, confidence, and reasoning displayed
9. **Database Updated**: Refinement automatically saved

---

## 6. Export Your Data

Three export options at the bottom:

### 📥 Download as CSV
- Instant download
- All columns included
- No formatting (plain text)
- Good for: Importing into spreadsheets

### 📊 Download as Excel
- Professional Excel file
- 3 sheets:
  - **Summary**: Statistics and overview
  - **Results**: Full table with all columns
  - **Raw_Data**: Complete JSON for debugging
- Good for: Sharing, reporting, presentations

### 📄 Download as JSON
- Complete analysis data
- All AI reasoning preserved
- Includes validation status, page references
- Good for: Integration with other systems

---

## 7. Workflow Example

**Scenario**: You extract a floor plan with 3 errors

```
1. Upload & Extract
   └─ All data automatically saved to database

2. Review Results
   └─ See 47 fields extracted, 5 have low confidence
   └─ 2 validation conflicts detected

3. Fix Validation Issues First
   └─ Refine the 2 conflicting fields
   └─ AI re-analyzes with your hints
   └─ Database updated automatically

4. Review Low Confidence Items
   └─ Check the 5 items with < 70% confidence
   └─ Refine the 2-3 that are actually wrong
   └─ Keep the ones that are ok (maybe just ambiguous)

5. Final Review
   └─ Read through AI Reasoning for critical fields
   └─ Spot-check a few calculations
   └─ Manual verification of key measurements

6. Export
   └─ Download Excel with final results
   └─ Project already saved in history
   └─ Can reload any time!

7. Next Project
   └─ Upload another PDF
   └─ Previous projects stay in sidebar history
   └─ Repeat workflow
```

---

## 8. Understanding AI Reasoning

The "AI Reasoning / Source" column is crucial. Examples:

**Good (High Confidence):**
```
"Found on Page 1, Title Block. Plan Number clearly printed as 'A-101'. Confidence 95%."
```

**Good (Calculated):**
```
"Page 2, Floor Plan. Using identified scale 1/4\" = 1'-0\". Sum of all exterior wall segments measured at scale = 312.5 LF. Validated against perimeter formula."
```

**Warning (Conflict):**
```
"Calculated perimeter = 150 LF, but printed dimension shows 145 LF. Discrepancy of 5 LF. Used printed dimension (confidence 60%)."
```

**Not Found:**
```
"No data found on any of the 5 pages reviewed. Data not present in provided images."
```

---

## 9. Validation Status Color Reference

Look for these colors in the "Validation Status" column:

- 🟢 **Green Background**: Verified data - high confidence, directly from plans
- 🟡 **Yellow Background**: Warning - calculated or inferred data
- 🔴 **Red Background**: Problem - conflict or inconsistency detected
- ⚪ **Gray Background**: Not found - data not in PDF

---

## 10. Tips & Best Practices

### Before Extracting
- Ensure PDF is clear (200 DPI default works well)
- Plan should be architectural/technical (not photos/renderings)
- Best results with: Floor plans, elevations, sections, foundation plans

### During Review
- Read the AI Reasoning column - it tells you everything
- Look at Validation Status for immediate problem indicators
- Check Page References to verify AI looked at right pages

### When Refining
- Be specific: "Page 2, bottom right, dimension reads 50 feet"
- One refinement per field
- AI is usually right about confidence - trust low confidence warnings

### After Export
- Keep CSV for archival (never changes)
- Keep Excel for sharing (includes full reasoning)
- Use JSON for system integration
- Keep project in history for 1-2 weeks, then archive if not needed

---

## 11. Keyboard Shortcuts / Pro Tips

### In Streamlit App
- `Ctrl+Click` on fields to open in new sections (depending on browser)
- Copy/paste from reasoning column to notes
- Scroll down in tables with many columns

### Database
- Projects auto-save immediately after extraction
- Delete button removes permanently (no undo!)
- All data is portable - can backup `extraction_projects.db`

---

## 12. Common Issues & Solutions

### "Extraction failed - Rate limit"
- **Answer**: API limit reached. Wait 15-30 seconds, try again
- **Prevent**: Space out extractions, don't extract multiple PDFs simultaneously

### "Refinement didn't update"
- **Check**: Did you see the success message?
- **Solution**: Reload the app (F5 or refresh browser)
- **Verify**: Check if change is in database (click project history to reload)

### "Can't see project in history"
- **Check**: Did extraction finish completely? (Look for success message)
- **Solution**: Try refreshing sidebar (click another project first, now you should see new one)

### "Confidence is low on many fields"
- **Normal**: PDFs with unclear dimensions often have lower confidence
- **Solution**: Refine the important fields, AI learns from your corrections
- **Consider**: 60% can still be correct - read the reasoning!

---

## 13. Accessing Historical Projects

Projects are stored in: `extraction_projects.db`

**To backup:**
```bash
cp extraction_projects.db extraction_projects_backup.db
```

**To restore:**
```bash
cp extraction_projects_backup.db extraction_projects.db
```

**To clear all projects:**
```bash
rm extraction_projects.db
# App will recreate with fresh schema on next run
```

---

## 14. Performance Notes

Typical timing for a 5-page architectural PDF:

- **PDF Processing**: ~5 seconds
- **Gemini Analysis**: ~90-180 seconds (depends on page count & complexity)
- **Database Save**: < 1 second
- **Total**: ~2-4 minutes

Refinement of single field:
- **Re-analysis**: ~30-60 seconds
- **Database Update**: < 1 second
- **Total**: ~1 minute

---

## 15. Ready to go!

You now have a professional-grade system for architectural data extraction with:

✅ Automatic project saving  
✅ Project history & reload  
✅ AI reasoning & traceability  
✅ Validation & quality control  
✅ Challenge/refine mechanism  
✅ Multiple export formats  
✅ Professional UI  
✅ Live activity log  

**Next steps:**
1. Upload a PDF
2. Review the results
3. Refine any errors
4. Export and use the data!

For detailed technical information, see `PROFESSIONAL_FEATURES.md`
