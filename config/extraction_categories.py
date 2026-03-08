"""
Dynamic extraction categories configuration based on Generic Key Measures CSV.
Uses standardized codes for all extracted fields.
Easily add, remove, or modify categories here.
"""

EXTRACTION_CATEGORIES = {
    "general": {
        "label": "General Information",
        "fields": [
            {"code": "PLAN_NO", "name": "plan_number", "display": "Plan Number", "uom": "", "category": "General"},
            {"code": "ELEV_VIEW", "name": "elevation", "display": "Elevation", "uom": "", "category": "General"},
            {"code": "STORIES", "name": "stories", "display": "Stories", "uom": "", "category": "General"},
            {"code": "WIDTH_FT", "name": "width", "display": "Width", "uom": "FT", "category": "General"},
            {"code": "DEPTH_FT", "name": "depth", "display": "Depth", "uom": "FT", "category": "General"},
            {"code": "BATH_COUNT", "name": "bathrooms", "display": "Bathrooms", "uom": "", "category": "General"},
            {"code": "BED_COUNT", "name": "bedrooms", "display": "Bedrooms", "uom": "", "category": "General"},
        ],
    },
    "measurements": {
        "label": "Measurements (Key Measures)",
        "fields": [
            {"code": "SL_HS", "name": "concrete_slab_area_house",
             "display": "Concrete Slab Area - House", "uom": "SF", "category": "Measurements"},
            {"code": "SL_GAR", "name": "concrete_slab_area_garage",
             "display": "Concrete Slab Area - Garage", "uom": "SF", "category": "Measurements"},
            {"code": "SL_TOTAL", "name": "concrete_slab_area_total",
             "display": "Concrete Slab Area - Total", "uom": "SF", "category": "Measurements"},
            {"code": "EW_LF", "name": "exterior_wall_linear",
             "display": "Exterior Wall Linear", "uom": "LF", "category": "Measurements"},
            {"code": "IW_LF", "name": "interior_wall_linear",
             "display": "Interior Wall Linear", "uom": "LF", "category": "Measurements"},
            {"code": "WIN_SINGLE", "name": "window_count_single",
             "display": "Window Count - Single Pane", "uom": "", "category": "Measurements"},
            {"code": "WIN_DOUBLE", "name": "window_count_double",
             "display": "Window Count - Double Pane", "uom": "", "category": "Measurements"},
            {"code": "WIN_TOTAL", "name": "window_count_total",
             "display": "Window Count - Total", "uom": "", "category": "Measurements"},
            {"code": "DOOR_EXT", "name": "door_count_exterior",
             "display": "Door Count - Exterior", "uom": "", "category": "Measurements"},
            {"code": "DOOR_INT", "name": "door_count_interior",
             "display": "Door Count - Interior", "uom": "", "category": "Measurements"},
            {"code": "DOOR_TOTAL", "name": "door_count_total",
             "display": "Door Count - Total", "uom": "", "category": "Measurements"},
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
