"""Script to create sample metadata pickle files for each environment."""

import pickle
from datetime import datetime
from pathlib import Path


def create_dev_metadata() -> dict:
    """Create DEV environment metadata - includes test/debug tables."""
    return {
        "schemas": {
            "public": {
                "tables": {
                    "student": ["id", "name", "email", "created_at", "updated_at"],
                    "course": ["id", "title", "description", "credits", "instructor_id"],
                    "enrollment": ["id", "student_id", "course_id", "enrolled_at", "grade"],
                    "instructor": ["id", "name", "email", "department"],
                    # Dev-only tables
                    "test_users": ["id", "test_name", "test_email"],
                    "debug_logs": ["id", "message", "level", "timestamp"],
                }
            },
            "hr": {
                "tables": {
                    "employee": ["emp_id", "first_name", "last_name", "email", "salary", "hire_date"],
                    "department": ["id", "name", "location", "budget"],
                    "payroll": ["id", "employee_id", "amount", "pay_date", "type"],
                }
            },
            "sales": {
                "tables": {
                    "customer": ["id", "name", "email", "phone", "address"],
                    "order": ["id", "customer_id", "order_date", "total_amount", "status"],
                    "product": ["id", "name", "description", "price", "stock_quantity"],
                    "order_item": ["id", "order_id", "product_id", "quantity", "unit_price"],
                }
            },
            # Dev-only schema
            "sandbox": {
                "tables": {
                    "experiment": ["id", "name", "config", "created_by"],
                    "temp_data": ["id", "data", "expires_at"],
                }
            },
        },
        "exported_at": datetime.now().isoformat(),
        "environment": "dev",
    }


def create_qa_metadata() -> dict:
    """Create QA environment metadata - similar to prod but with test data tables."""
    return {
        "schemas": {
            "public": {
                "tables": {
                    "student": ["id", "name", "email", "created_at", "updated_at"],
                    "course": ["id", "title", "description", "credits", "instructor_id"],
                    "enrollment": ["id", "student_id", "course_id", "enrolled_at", "grade"],
                    "instructor": ["id", "name", "email", "department"],
                }
            },
            "hr": {
                "tables": {
                    "employee": ["emp_id", "first_name", "last_name", "email", "salary", "hire_date"],
                    "department": ["id", "name", "location", "budget"],
                    "payroll": ["id", "employee_id", "amount", "pay_date", "type"],
                }
            },
            "sales": {
                "tables": {
                    "customer": ["id", "name", "email", "phone", "address"],
                    "order": ["id", "customer_id", "order_date", "total_amount", "status"],
                    "product": ["id", "name", "description", "price", "stock_quantity"],
                    "order_item": ["id", "order_id", "product_id", "quantity", "unit_price"],
                }
            },
        },
        "exported_at": datetime.now().isoformat(),
        "environment": "qa",
    }


def create_stage_metadata() -> dict:
    """Create STAGE environment metadata - mirrors prod structure."""
    return {
        "schemas": {
            "public": {
                "tables": {
                    "student": ["id", "name", "email", "created_at", "updated_at"],
                    "course": ["id", "title", "description", "credits", "instructor_id"],
                    "enrollment": ["id", "student_id", "course_id", "enrolled_at", "grade"],
                    "instructor": ["id", "name", "email", "department"],
                }
            },
            "hr": {
                "tables": {
                    "employee": ["emp_id", "first_name", "last_name", "email", "salary", "hire_date"],
                    "department": ["id", "name", "location", "budget"],
                    "payroll": ["id", "employee_id", "amount", "pay_date", "type"],
                }
            },
            "sales": {
                "tables": {
                    "customer": ["id", "name", "email", "phone", "address"],
                    "order": ["id", "customer_id", "order_date", "total_amount", "status"],
                    "product": ["id", "name", "description", "price", "stock_quantity"],
                    "order_item": ["id", "order_id", "product_id", "quantity", "unit_price"],
                }
            },
        },
        "exported_at": datetime.now().isoformat(),
        "environment": "stage",
    }


def create_prod_metadata() -> dict:
    """Create PROD environment metadata - production tables only."""
    return {
        "schemas": {
            "public": {
                "tables": {
                    "student": ["id", "name", "email", "created_at", "updated_at"],
                    "course": ["id", "title", "description", "credits", "instructor_id"],
                    "enrollment": ["id", "student_id", "course_id", "enrolled_at", "grade"],
                    "instructor": ["id", "name", "email", "department"],
                }
            },
            "hr": {
                "tables": {
                    "employee": ["emp_id", "first_name", "last_name", "email", "salary", "hire_date"],
                    "department": ["id", "name", "location", "budget"],
                    "payroll": ["id", "employee_id", "amount", "pay_date", "type"],
                }
            },
            "sales": {
                "tables": {
                    "customer": ["id", "name", "email", "phone", "address"],
                    "order": ["id", "customer_id", "order_date", "total_amount", "status"],
                    "product": ["id", "name", "description", "price", "stock_quantity"],
                    "order_item": ["id", "order_id", "product_id", "quantity", "unit_price"],
                }
            },
        },
        "exported_at": datetime.now().isoformat(),
        "environment": "prod",
    }


def save_pickle(data: dict, output_path: Path) -> None:
    """Save metadata to pickle file."""
    with open(output_path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


def count_stats(metadata: dict) -> tuple[int, int, int]:
    """Count schemas, tables, and columns in metadata."""
    schemas = metadata.get("schemas", {})
    schema_count = len(schemas)
    table_count = sum(len(s.get("tables", {})) for s in schemas.values())
    column_count = sum(
        len(cols)
        for s in schemas.values()
        for cols in s.get("tables", {}).values()
    )
    return schema_count, table_count, column_count


def main() -> None:
    """Create sample metadata pickle files for all environments."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Environment metadata generators
    environments = {
        "dev": create_dev_metadata,
        "qa": create_qa_metadata,
        "stage": create_stage_metadata,
        "prod": create_prod_metadata,
    }
    
    print("Creating metadata pickle files for all environments...\n")
    
    for env, create_func in environments.items():
        metadata = create_func()
        output_path = data_dir / f"metadata_{env}.pkl"
        save_pickle(metadata, output_path)
        
        schemas, tables, columns = count_stats(metadata)
        print(f"[{env.upper()}] {output_path.name}")
        print(f"       Schemas: {schemas}, Tables: {tables}, Columns: {columns}")
    
    print(f"\nAll files created in: {data_dir}")
    print("\nNote: DEV has extra test tables and sandbox schema that don't exist in PROD")


if __name__ == "__main__":
    main()
