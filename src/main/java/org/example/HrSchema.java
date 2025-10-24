package org.example;

import java.util.List;

public class HrSchema {
    public final Employee[] employees = {
        new Employee(1, "Alice", 60000),
        new Employee(2, "Bob", 40000),
        new Employee(3, "Charlie", 70000)
    };

    public static class Employee {
        public final int dept_id;
        public final String name;
        public final double salary;

        public Employee(int dept_id, String name, double salary) {
            this.dept_id = dept_id;
            this.name = name;
            this.salary = salary;
        }
    }
}
