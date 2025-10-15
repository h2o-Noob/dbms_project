import psycopg2
import json

# Connect to your PostgreSQL database
conn = psycopg2.connect(
    dbname="queryeq",
    user="h2o_arindam",     # or your username
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# Run an EXPLAIN query
cur.execute("EXPLAIN (FORMAT JSON) SELECT * FROM employees WHERE salary > 50000;")

# Fetch and parse the JSON plan
plan = cur.fetchone()[0][0]['Plan']
print(json.dumps(plan, indent=2))

# Close connection
cur.close()
conn.close()
