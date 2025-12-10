# db_service.py


import json
import os

class SchemaState:
    def __init__(self):
        self.metadata = {}
        self.table_name = None
        self.business_rules = []
        self.fallback_schema = {}
state = SchemaState()


def load_metadata(json_path: str):
    """Load JSON metadata from a static local file."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"[ERROR] Metadata file missing: {json_path}")

    try:
        with open(json_path, "r") as f:
            state.metadata = json.load(f)
    except Exception as e:
        raise Exception(f"[ERROR] Unable to load metadata: {e}")


def load_fallback_schema(json_path: str):
    """Load fallback schema to use if frontend schema is missing."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"[ERROR] Fallback schema file missing: {json_path}")

    try:
        with open(json_path, "r") as f:
            state.fallback_schema = json.load(f)
    except Exception as e:
        raise Exception(f"[ERROR] Unable to load fallback schema: {e}")


def set_table_name(name: str):
    """Static table name."""
    if not name:
        raise ValueError("[ERROR] Table name cannot be empty.")
    state.table_name = name


def set_business_rules(rules: list):
    """Business rules provided manually."""
    if not isinstance(rules, list):
        raise ValueError("[ERROR] Business rules must be a list.")
    state.business_rules = rules


def build_final_schema_description(frontend_schema: str):

    try:
        if frontend_schema and frontend_schema.strip():
            final_schema = frontend_schema
        else:
            raise ValueError("Frontend schema empty or missing")
    except Exception:
        final_schema = json.dumps(state.fallback_schema, indent=2)
        print("\n⚠️  WARNING: Frontend schema missing. Using fallback schema from local file.\n")

    description = "### SCHEMA DESCRIPTION ###\n"
    description += final_schema + "\n\n"

    description += "### TABLE NAME ###\n"
    description += f"{state.table_name}\n\n"

    description += "### LOCAL METADATA.json ###\n"
    description += json.dumps(state.metadata, indent=2) + "\n\n"

    description += "### BUSINESS RULES ###\n"
    for rule in state.business_rules:
        description += f"- {rule}\n"

    return description
