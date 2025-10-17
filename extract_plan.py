import psycopg2
import json

# Connect to your PostgreSQL database
conn = psycopg2.connect(
    dbname="postgres",
    #user=r"desktop-lon03s8\user",
    user="postgres",     # or your username
    host="localhost",
    port="5432",
    password="##"
)

cur = conn.cursor()
create_table_command = """
    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        age INT NOT NULL,
        salary REAL
    );
    """
cur.execute(create_table_command)

    # 3. Commit the table creation
conn.commit()
insert_data_command = """
    INSERT INTO employees (name, age, salary) VALUES
    ('Alice Johnson', 30, 65000.00),
    ('Bob Williams', 45, 80000.00),
    ('Charlie Brown', 25, 45000.00)
    ON CONFLICT DO NOTHING;
"""
cur.execute(insert_data_command)
conn.commit()
print("Data inserted.")
# Run an EXPLAIN query
cur.execute("EXPLAIN (FORMAT JSON) SELECT * FROM employees WHERE salary > 50000;")

# Fetch and parse the JSON plan
plan = cur.fetchone()[0][0]['Plan']
print(json.dumps(plan, indent=2))

# Close connection
cur.close()
conn.close()
