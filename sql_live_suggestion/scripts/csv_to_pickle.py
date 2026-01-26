"""
Script to convert a CSV file with database metadata to pickle format.

Expected CSV format (one row per column):
    schema,table,column
    public,student,id
    public,student,name
    public,student,email
    public,course,id
    public,course,title
    hr,employee,emp_id
    hr,employee,first_name
    ...

Usage:
    python scripts/csv_to_pickle.py input.csv dev
    python scripts/csv_to_pickle.py input.csv prod
    python scripts/csv_to_pickle.py input.csv qa --output custom_output.pkl
"""

import argparse
import csv
import pickle
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_csv(csv_path: str, schema_col: str, table_col: str, column_col: str) -> dict:
    """
    Load CSV and build hierarchical metadata structure.
    
    Args:
        csv_path: Path to the CSV file
        schema_col: Name of the schema column in CSV
        table_col: Name of the table column in CSV
        column_col: Name of the column column in CSV
    
    Returns:
        Dictionary in the expected pickle format
    """
    # Use nested defaultdict for easy building
    schemas = defaultdict(lambda: {"tables": defaultdict(list)})
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        # Validate headers
        headers = reader.fieldnames
        if not headers:
            raise ValueError("CSV file is empty or has no headers")
        
        # Check if expected columns exist
        missing = []
        if schema_col not in headers:
            missing.append(f"schema column '{schema_col}'")
        if table_col not in headers:
            missing.append(f"table column '{table_col}'")
        if column_col not in headers:
            missing.append(f"column column '{column_col}'")
        
        if missing:
            raise ValueError(
                f"Missing columns in CSV: {', '.join(missing)}. "
                f"Available columns: {', '.join(headers)}"
            )
        
        row_count = 0
        for row in reader:
            schema_name = row[schema_col].strip()
            table_name = row[table_col].strip()
            column_name = row[column_col].strip()
            
            # Skip empty rows
            if not schema_name or not table_name or not column_name:
                continue
            
            # Add column to the table (avoid duplicates)
            if column_name not in schemas[schema_name]["tables"][table_name]:
                schemas[schema_name]["tables"][table_name].append(column_name)
            
            row_count += 1
    
    # Convert defaultdict to regular dict
    result = {
        "schemas": {
            schema_name: {
                "tables": dict(schema_data["tables"])
            }
            for schema_name, schema_data in schemas.items()
        },
        "exported_at": datetime.now().isoformat(),
    }
    
    return result, row_count


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


def save_pickle(data: dict, output_path: Path) -> None:
    """Save metadata to pickle file."""
    with open(output_path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV database metadata to pickle format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage (outputs to data/metadata_dev.pkl)
    python scripts/csv_to_pickle.py mydata.csv dev
    
    # For production environment
    python scripts/csv_to_pickle.py prod_export.csv prod
    
    # Custom output path
    python scripts/csv_to_pickle.py mydata.csv dev --output /path/to/output.pkl
    
    # Custom column names in CSV
    python scripts/csv_to_pickle.py mydata.csv dev --schema-col SCHEMA_NAME --table-col TABLE_NAME --column-col COLUMN_NAME

Expected CSV format:
    schema,table,column
    public,student,id
    public,student,name
    public,course,id
    hr,employee,emp_id
        """,
    )
    
    parser.add_argument(
        "csv_file",
        help="Path to the input CSV file",
    )
    
    parser.add_argument(
        "environment",
        choices=["dev", "qa", "stage", "prod"],
        help="Environment name (determines output filename)",
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Custom output path (default: data/metadata_{env}.pkl)",
    )
    
    parser.add_argument(
        "--schema-col",
        default="schema",
        help="Name of the schema column in CSV (default: 'schema')",
    )
    
    parser.add_argument(
        "--table-col",
        default="table",
        help="Name of the table column in CSV (default: 'table')",
    )
    
    parser.add_argument(
        "--column-col",
        default="column",
        help="Name of the column column in CSV (default: 'column')",
    )
    
    args = parser.parse_args()
    
    # Validate input file
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return 1
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent / "data"
        data_dir.mkdir(exist_ok=True)
        output_path = data_dir / f"metadata_{args.environment}.pkl"
    
    print(f"Converting CSV to pickle...")
    print(f"  Input:  {csv_path}")
    print(f"  Output: {output_path}")
    print(f"  Environment: {args.environment}")
    print()
    
    try:
        # Load and convert
        metadata, row_count = load_csv(
            csv_path,
            schema_col=args.schema_col,
            table_col=args.table_col,
            column_col=args.column_col,
        )
        
        # Add environment to metadata
        metadata["environment"] = args.environment
        
        # Get stats
        schemas, tables, columns = count_stats(metadata)
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_pickle(metadata, output_path)
        
        print(f"✓ Successfully converted!")
        print(f"  Rows processed: {row_count}")
        print(f"  Schemas: {schemas}")
        print(f"  Tables: {tables}")
        print(f"  Columns: {columns}")
        print()
        print(f"  Output saved to: {output_path}")
        
        # Show sample of loaded data
        print()
        print("Sample of loaded schemas:")
        for i, (schema_name, schema_data) in enumerate(metadata["schemas"].items()):
            if i >= 3:
                remaining = len(metadata["schemas"]) - 3
                print(f"  ... and {remaining} more schemas")
                break
            tables_list = list(schema_data["tables"].keys())[:3]
            print(f"  • {schema_name}: {', '.join(tables_list)}{'...' if len(schema_data['tables']) > 3 else ''}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
