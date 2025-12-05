import re
import sys

class QuerySanitizer:
    def __init__(self):
        # Ordered list of regex replacements
        self.replacements = [
            # ==========================================
            # 1. Type Casting (The "::" operator)
            # ==========================================
            # Generic catch-all for ::type -> CAST(... AS type)
            # Captures 'table.col::type' or 'col::type' or 'value::type'
            (r'([a-zA-Z0-9_."\']+)::([a-zA-Z0-9_]+)', r'CAST(\1 AS \2)'),

            # Specific fixes for Postgres types -> Calcite Types after the generic cast
            (r'AS\s+int4\b', 'AS INTEGER'),
            (r'AS\s+int\b', 'AS INTEGER'),
            (r'AS\s+float8\b', 'AS DOUBLE'),
            (r'AS\s+float\b', 'AS DOUBLE'),
            (r'AS\s+text\b', 'AS VARCHAR'),
            (r'AS\s+bpchar\b', 'AS CHAR'),
            (r'AS\s+numeric\b', 'AS DECIMAL'),

            # ==========================================
            # 2. Date & Interval Arithmetic
            # ==========================================
            # Postgres allows "date - integer" (days). Calcite needs explicit INTERVAL.
            # Pattern: date '...' - 90
            (r"(date\s+'[^']+')\s*-\s*([0-9]+)\b", r"\1 - INTERVAL '\2' DAY"),
            (r"(date\s+'[^']+')\s*\+\s*([0-9]+)\b", r"\1 + INTERVAL '\2' DAY"),
            
            # Handle "now()" -> CURRENT_DATE or CURRENT_TIMESTAMP if present
            (r'\bnow\(\)', 'CURRENT_TIMESTAMP'),

            # ==========================================
            # 3. Pagination (LIMIT -> FETCH)
            # ==========================================
            # TPC-H uses "LIMIT N". Calcite strict ANSI uses "FETCH NEXT N ROWS ONLY".
            # Note: We use case-insensitive matching for 'limit'
            (r'\bLIMIT\s+(\d+)', r'FETCH NEXT \1 ROWS ONLY'),

            # ==========================================
            # 4. Cleanup & Normalization
            # ==========================================
            # Strip double quotes (Postgres case sensitivity) to standard unquoted
            (r'"', ''),
        ]

    def sanitize_sql(self, sql_query):
        """
        Applies all regex transformations to the input query.
        """
        clean_sql = sql_query
        
        # Apply Regex Replacements sequentially
        for pattern, replacement in self.replacements:
            clean_sql = re.sub(pattern, replacement, clean_sql, flags=re.IGNORECASE)
        
        # Final cleanup: ensure single spaces
        clean_sql = re.sub(r'\s+', ' ', clean_sql).strip()
        
        return clean_sql

    def generate_schema_ddl(self, metadata):
        """
        Generates standard CREATE TABLE statements with Constraints.
        """
        ddl_statements = []
        
        for table_name, info in metadata.items():
            columns = info.get("columns", {})
            pk = info.get("primary_key", [])
            fks = info.get("foreign_keys", []) # Added Foreign Key support
            
            stmt = f"CREATE TABLE {table_name} ("
            
            col_defs = []
            for col, dtype in columns.items():
                # Map Postgres types to standard types
                dtype_lower = dtype.lower()
                if "int" in dtype_lower or "serial" in dtype_lower:
                    std_type = "INTEGER"
                elif "float" in dtype_lower or "double" in dtype_lower:
                    std_type = "DOUBLE"
                elif "numeric" in dtype_lower or "decimal" in dtype_lower:
                    std_type = "DECIMAL"
                elif "date" in dtype_lower:
                    std_type = "DATE"
                else:
                    std_type = "VARCHAR"
                
                col_defs.append(f"{col} {std_type}")
            
            # Add Primary Key
            if pk:
                pk_str = ", ".join(pk)
                col_defs.append(f"PRIMARY KEY ({pk_str})")
            
            # Add Foreign Keys (Optional, but helpful for SQLSolver)
            # Format in metadata: [{"cols": ["n_regionkey"], "ref_table": "region", "ref_cols": ["r_regionkey"]}]
            for fk in fks:
                local_cols = ", ".join(fk["cols"])
                ref_table = fk["ref_table"]
                ref_cols = ", ".join(fk["ref_cols"])
                col_defs.append(f"FOREIGN KEY ({local_cols}) REFERENCES {ref_table}({ref_cols})")

            stmt += ", ".join(col_defs)
            stmt += ");"
            ddl_statements.append(stmt)
            
        return "\n".join(ddl_statements)

# ==========================================
# TEST HARNESS
# ==========================================
if __name__ == "__main__":
    sanitizer = QuerySanitizer()

    # Test Case: TPC-H Q2 style (LIMIT + ::type + Quotes)
    raw_query = """
    SELECT 
        s_acctbal, 
        s_name, 
        n_name, 
        p_partkey::int, 
        p_mfgr 
    FROM "Part", "Supplier"
    WHERE p_partkey = ps_partkey 
    AND l_shipdate <= date '1998-12-01' - 90
    ORDER BY s_acctbal DESC 
    LIMIT 100;
    """
    
    print("--- Input SQL ---")
    print(raw_query.strip())
    
    clean_sql = sanitizer.sanitize_sql(raw_query)
    
    print("\n--- Output SQL (Calcite Ready) ---")
    print(clean_sql)
    
    # Expected improvements:
    # 1. "Part" -> Part
    # 2. p_partkey::int -> CAST(p_partkey AS INTEGER)
    # 3. date ... - 90 -> date ... - INTERVAL '90' DAY
    # 4. LIMIT 100 -> FETCH NEXT 100 ROWS ONLY