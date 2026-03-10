"""
Dynamic extraction categories configuration — Generic Key Measures taxonomy.
Uses standardized codes for all extracted fields.
Organized into construction trade groups aligned with standard estimating practice.
"""

EXTRACTION_CATEGORIES = {

    # ─────────────────────────────────────────────────────────────────────────
    # GENERAL INFORMATION
    # ─────────────────────────────────────────────────────────────────────────
    "general": {
        "label": "General Information",
        "fields": [
            {"code": "PLAN_NO",     "name": "plan_number",  "display": "Plan Number",   "uom": "",   "category": "General"},
            {"code": "ELEV_VIEW",   "name": "elevation",    "display": "Elevation",     "uom": "",   "category": "General"},
            {"code": "STORIES",     "name": "stories",      "display": "Stories",       "uom": "",   "category": "General"},
            {"code": "WIDTH_FT",    "name": "width",        "display": "Width",         "uom": "FT", "category": "General"},
            {"code": "DEPTH_FT",    "name": "depth",        "display": "Depth",         "uom": "FT", "category": "General"},
            {"code": "BATH_COUNT",  "name": "bathrooms",    "display": "Bathrooms",     "uom": "",   "category": "General"},
            {"code": "BED_COUNT",   "name": "bedrooms",     "display": "Bedrooms",      "uom": "",   "category": "General"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # FOUNDATIONS & SLABS
    # ─────────────────────────────────────────────────────────────────────────
    "foundations": {
        "label": "Foundations & Slabs",
        "fields": [
            {"code": "SL_TOTAL",    "name": "slab_total",       "display": "Concrete Slab - Total",   "uom": "SF", "category": "Foundations"},
            {"code": "SL_HS",       "name": "slab_house",       "display": "Concrete Slab - House",   "uom": "SF", "category": "Foundations"},
            {"code": "SL_GAR",      "name": "slab_garage",      "display": "Concrete Slab - Garage",  "uom": "SF", "category": "Foundations"},
            {"code": "SL_POR",      "name": "slab_porch",       "display": "Concrete Slab - Porches", "uom": "SF", "category": "Foundations"},
            {"code": "FND_FTG",     "name": "footing_linear",   "display": "Concrete Footings",       "uom": "LF", "category": "Foundations"},
            {"code": "FND_FTG_PAD", "name": "footing_pads",     "display": "Footing Pads",            "uom": "EA", "category": "Foundations"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # EXTERIOR WALLS
    # ─────────────────────────────────────────────────────────────────────────
    "exterior_walls": {
        "label": "Exterior Walls",
        "fields": [
            {"code": "WE_TOTAL", "name": "ext_wall_total", "display": "Exterior Wall - Total",    "uom": "LF", "category": "Exterior Walls"},
            {"code": "WE_2x4",   "name": "ext_wall_2x4",  "display": "Exterior Wall - 2x4",      "uom": "LF", "category": "Exterior Walls"},
            {"code": "WE_2x6",   "name": "ext_wall_2x6",  "display": "Exterior Wall - 2x6",      "uom": "LF", "category": "Exterior Walls"},
            {"code": "WE_CMU",   "name": "ext_wall_cmu",  "display": "Exterior Wall - CMU Block", "uom": "LF", "category": "Exterior Walls"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # INTERIOR WALLS
    # ─────────────────────────────────────────────────────────────────────────
    "interior_walls": {
        "label": "Interior Walls",
        "fields": [
            {"code": "WI_TOTAL", "name": "int_wall_total",  "display": "Interior Wall - Total",      "uom": "LF", "category": "Interior Walls"},
            {"code": "WI_2x4",   "name": "int_wall_2x4",   "display": "Interior Wall - 2x4",        "uom": "LF", "category": "Interior Walls"},
            {"code": "WI_2x6",   "name": "int_wall_2x6",   "display": "Interior Wall - 2x6",        "uom": "LF", "category": "Interior Walls"},
            {"code": "WI_MTL",   "name": "int_wall_metal", "display": "Interior Wall - Metal Stud", "uom": "LF", "category": "Interior Walls"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # CEILINGS / DRYWALL
    # ─────────────────────────────────────────────────────────────────────────
    "ceilings": {
        "label": "Ceilings & Drywall",
        "fields": [
            {"code": "CE_DW",     "name": "ceiling_dw_house",  "display": "Ceiling Drywall - House",  "uom": "SF", "category": "Ceilings"},
            {"code": "CE_POR",    "name": "ceiling_dw_porch",  "display": "Ceiling Drywall - Porch",  "uom": "SF", "category": "Ceilings"},
            {"code": "CE_DW_GAR", "name": "ceiling_dw_garage", "display": "Ceiling Drywall - Garage", "uom": "SF", "category": "Ceilings"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # SHEATHING
    # ─────────────────────────────────────────────────────────────────────────
    "sheathing": {
        "label": "Sheathing",
        "fields": [
            {"code": "SH_FL",      "name": "sheath_floor",       "display": "Sheathing - Floor",           "uom": "SF", "category": "Sheathing"},
            {"code": "SH_RF",      "name": "sheath_roof",        "display": "Sheathing - Roof",            "uom": "SF", "category": "Sheathing"},
            {"code": "SH_RF_FIRE", "name": "sheath_roof_fire",   "display": "Sheathing - Roof Fire Rated", "uom": "SF", "category": "Sheathing"},
            {"code": "SH_WA_GBL",  "name": "sheath_wall_gable",  "display": "Sheathing - Wall Gable",      "uom": "SF", "category": "Sheathing"},
            {"code": "SH_WA",      "name": "sheath_wall",        "display": "Sheathing - Wall",            "uom": "SF", "category": "Sheathing"},
            {"code": "SH_WA_FIRE", "name": "sheath_wall_fire",   "display": "Sheathing - Wall Fire Rated", "uom": "SF", "category": "Sheathing"},
            {"code": "SH_WA_OSB",  "name": "sheath_wall_osb",    "display": "Sheathing - Wall OSB",        "uom": "SF", "category": "Sheathing"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # ROOFING
    # ─────────────────────────────────────────────────────────────────────────
    "roofing": {
        "label": "Roofing",
        "fields": [
            {"code": "RF_AREA",  "name": "roof_area",       "display": "Roof - Total Area",    "uom": "SF", "category": "Roofing"},
            {"code": "RF_EV",    "name": "roof_eave",       "display": "Roof - Eave",          "uom": "LF", "category": "Roofing"},
            {"code": "RF_HP",    "name": "roof_hip",        "display": "Roof - Hip",           "uom": "LF", "category": "Roofing"},
            {"code": "RF_RK",    "name": "roof_rake",       "display": "Roof - Rake",          "uom": "LF", "category": "Roofing"},
            {"code": "RF_RDG",   "name": "roof_ridge_cap",  "display": "Roof - Ridge Cap",     "uom": "LF", "category": "Roofing"},
            {"code": "RF_VL",    "name": "roof_valley",     "display": "Roof - Valley",        "uom": "LF", "category": "Roofing"},
            {"code": "RF_RKW",   "name": "roof_rake_wall",  "display": "Roof - Rake to Wall",  "uom": "LF", "category": "Roofing"},
            {"code": "RF_EVW",   "name": "roof_eave_wall",  "display": "Roof - Eave to Wall",  "uom": "LF", "category": "Roofing"},
            {"code": "RF_RDGV",  "name": "roof_ridge_vent", "display": "Roof - Ridge Vent",    "uom": "LF", "category": "Roofing"},
            {"code": "RF_VNT",   "name": "roof_pod_vent",   "display": "Roof - Pod Vent",      "uom": "EA", "category": "Roofing"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # SIDING / EXTERIOR FINISHES
    # ─────────────────────────────────────────────────────────────────────────
    "siding": {
        "label": "Siding & Exterior Finishes",
        "fields": [
            {"code": "EF_HS",           "name": "siding_lap",           "display": "Siding - Horizontal/Lap",       "uom": "SF", "category": "Siding"},
            {"code": "EF_BNB",          "name": "siding_bnb",           "display": "Siding - Board & Batten",        "uom": "SF", "category": "Siding"},
            {"code": "EF_SHK",          "name": "siding_shake",         "display": "Siding - Shake",                 "uom": "SF", "category": "Siding"},
            {"code": "EF_STN",          "name": "siding_stone",         "display": "Siding - Stone Veneer",          "uom": "SF", "category": "Siding"},
            {"code": "EF_BRI",          "name": "siding_brick",         "display": "Siding - Brick",                 "uom": "SF", "category": "Siding"},
            {"code": "EF_BRI_SOLDIER",  "name": "siding_brick_soldier", "display": "Siding - Brick Soldier Course",  "uom": "LF", "category": "Siding"},
            {"code": "EF_BRI_ROWLOCK",  "name": "siding_brick_rowlock", "display": "Siding - Brick Rowlock Course",  "uom": "LF", "category": "Siding"},
            {"code": "EF_STN_SOLDIER",  "name": "siding_stone_soldier", "display": "Siding - Stone Soldier Course",  "uom": "LF", "category": "Siding"},
            {"code": "EF_WTRTBL",       "name": "siding_watertable",    "display": "Siding - Watertable",            "uom": "LF", "category": "Siding"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # LINTELS
    # ─────────────────────────────────────────────────────────────────────────
    "lintels": {
        "label": "Lintels",
        "fields": [
            {"code": "LINTEL_3x3x14_4",     "name": "lintel_steel_3x3",    "display": "Lintel - 3-1/2x3-1/2x1/4 Steel Angle", "uom": "LF", "category": "Lintels"},
            {"code": "LINTEL_10_6_PRECAST",  "name": "lintel_precast_10_6", "display": "Lintel - 10-6 Precast",                 "uom": "LF", "category": "Lintels"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # EXTERIOR TRIMS & ACCESSORIES
    # ─────────────────────────────────────────────────────────────────────────
    "trims": {
        "label": "Exterior Trims & Accessories",
        "fields": [
            {"code": "TE_CNR",    "name": "trim_corner",     "display": "Trim - Corner",           "uom": "LF", "category": "Trims"},
            {"code": "TE_SHR",    "name": "trim_shutters",   "display": "Trim - Shutters",         "uom": "EA", "category": "Trims"},
            {"code": "TE_SOFFIT", "name": "trim_soffit",     "display": "Trim - Soffit",           "uom": "LF", "category": "Trims"},
            {"code": "TE_FASCIA", "name": "trim_fascia",     "display": "Trim - Fascia",           "uom": "LF", "category": "Trims"},
            {"code": "TE_ZFLASH", "name": "trim_z_flash",    "display": "Trim - Z-Flashing",       "uom": "LF", "category": "Trims"},
            {"code": "TE_FOAM",   "name": "trim_foam",       "display": "Trim - Foam Trim Pieces", "uom": "EA", "category": "Trims"},
            {"code": "TE_DS",     "name": "trim_downspouts", "display": "Trim - Down Spouts",      "uom": "EA", "category": "Trims"},
            {"code": "TE_GUTTER", "name": "trim_gutter",     "display": "Trim - Gutters",          "uom": "LF", "category": "Trims"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # DOORS & CASING
    # ─────────────────────────────────────────────────────────────────────────
    "doors": {
        "label": "Doors & Casing",
        "fields": [
            {"code": "DOOR_EXT",       "name": "door_exterior",      "display": "Door - Exterior (Total)",      "uom": "EA", "category": "Doors"},
            {"code": "DOOR_INT",       "name": "door_interior",      "display": "Door - Interior (Total)",      "uom": "EA", "category": "Doors"},
            {"code": "DOOR_TOTAL",     "name": "door_total",         "display": "Door - All (Total)",           "uom": "EA", "category": "Doors"},
            {"code": "DI_SW",          "name": "door_int_single_sw", "display": "Door - Interior Single Swing", "uom": "EA", "category": "Doors"},
            {"code": "DI_2SW",         "name": "door_int_double_sw", "display": "Door - Interior Double Swing", "uom": "EA", "category": "Doors"},
            {"code": "LF_DOOR_CASING", "name": "door_casing_lf",    "display": "Door Casing - Linear",         "uom": "LF", "category": "Doors"},
            {"code": "INT_CASING",     "name": "int_casing_ea",      "display": "Interior Casing (Openings)",   "uom": "EA", "category": "Doors"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # WINDOWS
    # ─────────────────────────────────────────────────────────────────────────
    "windows": {
        "label": "Windows",
        "fields": [
            {"code": "WIN_TOTAL",  "name": "window_total",  "display": "Window - Total Count", "uom": "EA", "category": "Windows"},
            {"code": "WIN_SINGLE", "name": "window_single", "display": "Window - Single Pane", "uom": "EA", "category": "Windows"},
            {"code": "WIN_DOUBLE", "name": "window_double", "display": "Window - Double Pane", "uom": "EA", "category": "Windows"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # PLUMBING (placeholders — extracted from fixture schedules if present)
    # ─────────────────────────────────────────────────────────────────────────
    "plumbing": {
        "label": "Plumbing (Fixtures)",
        "fields": [
            {"code": "PLB_BATH", "name": "plumb_bath",    "display": "Plumbing - Bath Fixtures",    "uom": "EA", "category": "Plumbing"},
            {"code": "PLB_KIT",  "name": "plumb_kitchen", "display": "Plumbing - Kitchen Fixtures", "uom": "EA", "category": "Plumbing"},
            {"code": "PLB_LAU",  "name": "plumb_laundry", "display": "Plumbing - Laundry Hookups",  "uom": "EA", "category": "Plumbing"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # CABINETRY (placeholders — extracted from cabinet schedules if present)
    # ─────────────────────────────────────────────────────────────────────────
    "cabinetry": {
        "label": "Cabinetry",
        "fields": [
            {"code": "CAB_KIT_BASE", "name": "cab_kitchen_base",  "display": "Cabinet - Kitchen Base",  "uom": "LF", "category": "Cabinetry"},
            {"code": "CAB_KIT_UPPR", "name": "cab_kitchen_upper", "display": "Cabinet - Kitchen Upper", "uom": "LF", "category": "Cabinetry"},
            {"code": "CAB_BATH",     "name": "cab_bath",          "display": "Cabinet - Bath Vanity",   "uom": "LF", "category": "Cabinetry"},
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # INSULATION (placeholders — extracted from insulation notes if present)
    # ─────────────────────────────────────────────────────────────────────────
    "insulation": {
        "label": "Insulation",
        "fields": [
            {"code": "INS_WA",  "name": "insul_wall",    "display": "Insulation - Wall",    "uom": "SF", "category": "Insulation"},
            {"code": "INS_CLG", "name": "insul_ceiling", "display": "Insulation - Ceiling", "uom": "SF", "category": "Insulation"},
            {"code": "INS_FLR", "name": "insul_floor",   "display": "Insulation - Floor",   "uom": "SF", "category": "Insulation"},
        ],
    },
}


def get_all_fields():
    """Get a flat list of all extraction fields."""
    fields = []
    for category in EXTRACTION_CATEGORIES.values():
        fields.extend(category["fields"])
    return fields


def get_field_names():
    """Get list of all field names for easy reference."""
    return [field["name"] for field in get_all_fields()]


def get_field_codes():
    """Get list of all field codes for reference."""
    return [field["code"] for field in get_all_fields()]


def get_field_by_code(code: str):
    """Get field definition by code."""
    for field in get_all_fields():
        if field["code"] == code:
            return field
    return None


def get_field_by_name(name: str):
    """Get field definition by name."""
    for field in get_all_fields():
        if field["name"] == name:
            return field
    return None
