package org.example;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.calcite.plan.RelOptUtil;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.sql.SqlKind;
import org.apache.calcite.sql.fun.SqlStdOperatorTable;
import org.apache.calcite.tools.Frameworks;
import org.apache.calcite.tools.RelBuilder;
import org.apache.calcite.rex.RexNode;
import org.apache.calcite.schema.SchemaPlus;
import org.apache.calcite.schema.impl.AbstractTable;
import org.apache.calcite.rel.type.RelDataType;
import org.apache.calcite.rel.type.RelDataTypeFactory;
import org.apache.calcite.sql.type.SqlTypeName;

import java.io.File;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class App {

    public static void main(String[] args) throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        JsonNode root = mapper.readTree(new File("plan.json"));
        JsonNode planNode = root.get(0).get("Plan");

        SchemaPlus rootSchema = Frameworks.createRootSchema(true);
        registerTablesFromPlan(rootSchema, planNode);

        RelBuilder builder = RelBuilder.create(
                Frameworks.newConfigBuilder()
                        .defaultSchema(rootSchema)
                        .build()
        );

        convertPlan(builder, planNode); // build plan on stack
RelNode relNode = builder.build(); // final build after stack is ready
System.out.println("=== Relational Algebra ===");
System.out.println(RelOptUtil.toString(relNode));

    }

    private static void registerTablesFromPlan(SchemaPlus schema, JsonNode node) {
        Set<String> tables = new HashSet<>();
        collectTables(node, tables);
        for (String table : tables) {
            schema.add("lineitem", new AbstractTable() {
                @Override
                public RelDataType getRowType(RelDataTypeFactory typeFactory) {
                    return typeFactory.builder()
                            .add("l_orderkey", SqlTypeName.INTEGER)
                            .add("l_shipdate", SqlTypeName.DATE)
                            .build();
                }
            });            
        }
    }
    

    private static void collectTables(JsonNode node, Set<String> tables) {
        if (node == null) return;
        if (node.has("Relation Name")) {
            tables.add(node.get("Relation Name").asText());
        }
        if (node.has("Plans")) {
            for (JsonNode sub : node.get("Plans")) {
                collectTables(sub, tables);
            }
        }
    }

    private static void convertPlan(RelBuilder builder, JsonNode node) {
        String nodeType = node.get("Node Type").asText();
    
        switch (nodeType) {
            case "Seq Scan":
            case "Index Scan":
                String table = node.get("Relation Name").asText();
                builder.scan(table);
                if (node.has("Filter")) {
                    RexNode filter = parseFilter(builder, node.get("Filter").asText());
                    if (filter != null)
                        builder.filter(filter);
                }
                break;
    
            case "HashAggregate":
            case "Aggregate":
                JsonNode subPlanAgg = node.get("Plans").get(0);
                convertPlan(builder, subPlanAgg); // recursive call
                List<String> groupKeys = new ArrayList<>();
                if (node.has("Group Key")) {
                    node.get("Group Key").forEach(k -> groupKeys.add(k.asText()));
                }
                if (!groupKeys.isEmpty()) {
                    builder.aggregate(builder.groupKey(groupKeys.toArray(new String[0])));
                } else {
                    builder.aggregate(builder.groupKey());
                }
                break;
    
            case "Hash Join":
            case "Merge Join":
            case "Nested Loop":
                JsonNode left = node.get("Plans").get(0);
                JsonNode right = node.get("Plans").get(1);
                convertPlan(builder, left);
                RelNode leftNode = builder.build(); // temporarily build left
                builder.push(leftNode);
                convertPlan(builder, right);
                RexNode condition = parseJoinCondition(builder, node);
                builder.join(org.apache.calcite.rel.core.JoinRelType.INNER, condition);
                break;
    
            case "Sort":
                JsonNode subPlanSort = node.get("Plans").get(0);
                convertPlan(builder, subPlanSort);
                break;
    
            case "Limit":
                JsonNode subPlanLimit = node.get("Plans").get(0);
                convertPlan(builder, subPlanLimit);
                int limit = node.has("Plan Rows") ? node.get("Plan Rows").asInt() : 10;
                builder.limit(0, limit);
                break;
    
            case "Project":
                JsonNode subPlanProj = node.get("Plans").get(0);
                convertPlan(builder, subPlanProj);
                break;
    
            default:
                throw new RuntimeException("Unsupported Node Type: " + nodeType);
        }
    }    

    private static RexNode parseFilter(RelBuilder builder, String filter) {
        try {
            filter = filter.replace("(", "").replace(")", "").trim();
            if (filter.contains("<")) {
                String[] parts = filter.split("<");
                return builder.call(SqlStdOperatorTable.LESS_THAN,
                        builder.field(trim(parts[0])),
                        builder.literal(parseLiteral(trim(parts[1])))
                );
            } else if (filter.contains(">")) {
                String[] parts = filter.split(">");
                return builder.call(SqlStdOperatorTable.GREATER_THAN,
                        builder.field(trim(parts[0])),
                        builder.literal(parseLiteral(trim(parts[1])))
                );
            } else if (filter.contains("=")) {
                String[] parts = filter.split("=");
                return builder.call(SqlStdOperatorTable.EQUALS,
                        builder.field(trim(parts[0])),
                        builder.literal(parseLiteral(trim(parts[1])))
                );
            }
        } catch (Exception e) {
            System.err.println("Could not parse filter: " + filter);
        }
        return null;
    }
    
    private static Object parseLiteral(String value) {
        value = value.replace("::date", "").replace("::int", "").replace("'", "").trim();
        if (value.matches("\\d+")) {
            return Integer.parseInt(value);
        } else if (value.matches("\\d+\\.\\d+")) {
            return Double.parseDouble(value);
        } else {
            return value; // string/date literal
        }
    }
    
    

    private static RexNode parseJoinCondition(RelBuilder builder, JsonNode node) {
        if (!node.has("Hash Cond") && !node.has("Merge Cond"))
            return builder.literal(true);

        String cond = node.has("Hash Cond") ? node.get("Hash Cond").asText() :
                node.get("Merge Cond").asText();
        cond = cond.replace("(", "").replace(")", "");

        if (cond.contains("=")) {
            String[] parts = cond.split("=");
            return builder.call(SqlStdOperatorTable.EQUALS,
                    builder.field(trim(parts[0])),
                    builder.field(trim(parts[1])));
        }
        return builder.literal(true);
    }

    private static String trim(String s) {
        return s.trim().replaceAll("^['\"]|['\"]$", "");
    }
}
