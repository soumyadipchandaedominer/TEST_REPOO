# db_service.py

import json
import os
import pyodbc  # pip install pyodbc

class SchemaState:
    def __init__(self):
        self.metadata = {}
        self.table_name = None
        self.business_rules = []
        self.fallback_schema = {}
        self.connection = None
        self.cursor = None

state = SchemaState()


def connect_to_sqlserver(server: str, database: str, username: str = None, password: str = None, 
                         trusted_connection: bool = True, driver: str = None):
    """SS
    Connect to SQL Server.
    
    Args:
        server: Server name (e.g., 'localhost' or 'SERVER\\INSTANCE')
        database: Database name
        username: SQL Server username (if not using Windows Authentication)
        password: SQL Server password (if not using Windows Authentication)
        trusted_connection: Use Windows Authentication (default: True)
        driver: ODBC driver name (auto-detected if None)
    
    Returns:
        Connection object
    """
    try:
        # Auto-detect driver if not specified
        if driver is None:
            drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]
            if not drivers:
                raise Exception("No SQL Server ODBC driver found. Please install one.")
            driver = drivers[0]  # Use the first available driver
            print(f"Using driver: {driver}")
        
        # Build connection string
        if trusted_connection:
            # Windows Authentication
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
            )
        else:
            # SQL Server Authentication
            if not username or not password:
                raise ValueError("Username and password required for SQL Server Authentication")
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
            )
        
        # Establish connection
        state.connection = pyodbc.connect(conn_str)
        state.cursor = state.connection.cursor()
        print(f"✓ Connected to SQL Server: {server}/{database}")
        
        return state.connection
        
    except pyodbc.Error as e:
        raise Exception(f"[ERROR] SQL Server connection failed: {e}")


def disconnect_from_sqlserver():
    """Close SQL Server connection."""
    try:
        if state.cursor:
            state.cursor.close()
        if state.connection:
            state.connection.close()
        print("✓ Disconnected from SQL Server")
    except Exception as e:
        print(f"[WARNING] Error during disconnect: {e}")


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """
    Execute a SQL query.
    
    Args:
        query: SQL query string
        params: Query parameters (for parameterized queries)
        fetch: Whether to fetch results (SELECT) or not (INSERT/UPDATE/DELETE)
    
    Returns:
        List of rows for SELECT queries, or row count for DML queries
    """
    if not state.connection:
        raise Exception("[ERROR] Not connected to database. Call connect_to_sqlserver() first.")
    
    try:
        if params:
            state.cursor.execute(query, params)
        else:
            state.cursor.execute(query)
        
        if fetch:
            # Fetch results for SELECT queries
            columns = [column[0] for column in state.cursor.description]
            results = []
            for row in state.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        else:
            # Commit for INSERT/UPDATE/DELETE
            state.connection.commit()
            return state.cursor.rowcount
            
    except pyodbc.Error as e:
        state.connection.rollback()
        raise Exception(f"[ERROR] Query execution failed: {e}")


def get_table_schema_from_db(table_name: str = None):
    """
    Retrieve table schema from SQL Server.
    
    Args:
        table_name: Table name (uses state.table_name if not provided)
    
    Returns:
        List of column information dictionaries
    """
    table = table_name or state.table_name
    if not table:
        raise ValueError("[ERROR] Table name not specified")
    
    query = """
    SELECT 
        COLUMN_NAME,
        DATA_TYPE,
        IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION
    """
    
    return execute_query(query, (table,), fetch=True)


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


# Example usage
if __name__ == "__main__":
    # SQL Server Authentication
    connect_to_sqlserver(
        server="103.172.151.143",
        database="SSR",
        username="sa",
        password="clouderp123!",
        trusted_connection=False
    )
    
    # Set table name and get schema
    set_table_name("Documents")
    schema = get_table_schema_from_db()
    print(json.dumps(schema, indent=2))
    
    # Execute a SELECT query
    results = execute_query("SELECT * FROM Documents")
    print(results)
    
    # Clean up
    disconnect_from_sqlserver()