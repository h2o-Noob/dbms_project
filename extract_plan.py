import psycopg2
import json
import os

# === PostgreSQL Connection Config ===
DB_CONFIG = {
    "dbname": "tpch",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

# === Target Query ===
QUERY = """
SELECT l_orderkey, 
       SUM(l_extendedprice * (1 - l_discount)) AS revenue
FROM lineitem
WHERE l_shipdate < DATE '1995-03-15'
GROUP BY l_orderkey;
"""

# === Output Directory ===
OUTPUT_DIR = "./plans_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_explain(cursor, query, settings_name, settings_sql=None):
    """
    Run EXPLAIN (FORMAT JSON) on a query with optional planner settings.
    """
    if settings_sql:
        for stmt in settings_sql:
            cursor.execute(stmt)

    cursor.execute(f"EXPLAIN (FORMAT JSON) {query}")
    result = cursor.fetchall()
    plan_json = result[0][0]  # PostgreSQL returns JSON as text inside a list
    plan_obj = plan_json[0]   # Extract the first plan object

    # Save to file
    filename = os.path.join(OUTPUT_DIR, f"{settings_name}.json")
    with open(filename, "w") as f:
        json.dump(plan_obj, f, indent=2)

    print(f"✅ Saved plan: {filename}")

    # Reset settings after each run
    cursor.execute("RESET ALL;")


def main():
    # Connect to PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Connected to PostgreSQL.\nGenerating plans...")

    # === 1️⃣ Default Plan ===
    run_explain(cur, QUERY, "default_plan")

    # === 2️⃣ Disable Hash Join ===
    run_explain(cur, QUERY, "no_hash_join", ["SET enable_hashjoin = off;"])

    # === 3️⃣ Disable Hash + Merge Join (force Nested Loop) ===
    run_explain(
        cur,
        QUERY,
        "nested_loop_only",
        ["SET enable_hashjoin = off;", "SET enable_mergejoin = off;"]
    )

    # === 4️⃣ Enable Parallel Workers ===
    run_explain(
        cur,
        QUERY,
        "parallel_plan",
        ["SET max_parallel_workers_per_gather = 2;"]
    )

    cur.close()
    conn.close()
    print("\n🎉 Done! Plans saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
