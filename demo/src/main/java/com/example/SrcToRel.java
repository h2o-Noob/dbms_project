package com.example;

import org.apache.calcite.adapter.jdbc.JdbcSchema;
import org.apache.calcite.config.Lex;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.rel.RelRoot;
import org.apache.calcite.rel.externalize.RelJsonWriter;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.sql.SqlNode;
import org.apache.calcite.sql.parser.SqlParser;
import org.apache.calcite.tools.FrameworkConfig;
import org.apache.calcite.tools.Frameworks;
import org.apache.calcite.tools.Planner;
import org.apache.calcite.tools.ValidationException;
import org.apache.commons.dbcp2.BasicDataSource;

public class SrcToRel {
    public static void main(String[] args) throws Exception {
        String sql = "SELECT * FROM employees WHERE salary > 50000";

        // PostgreSQL connection details
        String postgresUrl = "jdbc:postgresql://localhost:5432/postgres";
        String postgresUser = "postgres";
        String postgresPassword = "##";

        // Create a basic data source for PostgreSQL
        BasicDataSource dataSource = new BasicDataSource();
        dataSource.setUrl(postgresUrl);
        dataSource.setUsername(postgresUser);
        dataSource.setPassword(postgresPassword);

        // Get the root schema
        SchemaPlus rootSchema = Frameworks.createRootSchema(true);
        
        JdbcSchema jdbcSchema = JdbcSchema.create(rootSchema, "postgres_db", dataSource, null, "public");
        SchemaPlus postgresSchema = rootSchema.add("postgres_db",jdbcSchema);

        // Create the JDBC schema and add it to the root

        // 1) Create a Calcite planner with the JDBC sub-schema as the default.
        FrameworkConfig config = Frameworks.newConfigBuilder()
            .parserConfig(SqlParser.configBuilder()
                .setLex(Lex.JAVA)
                .build())
            // Set the `postgresSchema` as the default schema.
            // This is the object that was correctly populated above.
            .defaultSchema(postgresSchema)
            .build();

        // Planner creation must be within a try-catch block
        try {
            Planner planner = Frameworks.getPlanner(config);

            // 2) Parse
            SqlNode parsed = planner.parse(sql);
            System.out.println("=== Parsed SQL AST ===");
            System.out.println(parsed.toString());

            // 3) Validate
            SqlNode validated = planner.validate(parsed);
            System.out.println("\n=== Validated SQL ===");
            System.out.println(validated.toString());

            // 4) Convert to relational algebra (RelNode)
            RelRoot relRoot = planner.rel(validated);
            RelNode relNode = relRoot.rel;

            // 5) Print RelNode tree (human-readable)
            System.out.println("\n=== Relational algebra (RelNode) ===");
            System.out.println(RelOptUtil.toString(relNode));

            // 6) Optionally: write RelNode to JSON using RelJsonWriter
            System.out.println("\n=== RelNode as JSON (RelJsonWriter) ===");
            RelJsonWriter jsonWriter = new RelJsonWriter();
            relNode.explain(jsonWriter);
            System.out.println(jsonWriter.asString());

        } catch (ValidationException e) {
            System.err.println("Validation Error: " + e.getMessage());
        } finally {
            if (dataSource != null) {
                dataSource.close();
            }
        }
    }
}