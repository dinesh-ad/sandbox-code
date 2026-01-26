#!/usr/bin/env python3
"""
Command-line interface for SQL Live Suggestion (Standalone).

Usage:
    python -m standalone.cli <scope> <name> [schema] [table]
    
    Or from project root:
    python standalone/cli.py <scope> <name> [schema] [table]

Examples:
    python standalone/cli.py table student public
    python standalone/cli.py table studnt public
    python standalone/cli.py column email public student
    python standalone/cli.py schema public
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import standalone as a package
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import from standalone package
from standalone.metadata_cache import MetadataCache
from standalone.validator import Validator


def print_result(result, name: str):
    """Print validation result in a user-friendly format."""
    if result.is_valid():
        print(f"✓ VALID: '{result.match}'")
        return 0
    elif result.has_suggestions():
        print(f"? SUGGESTIONS for '{name}':")
        for s in result.suggestions:
            print(f"    → {s.name} ({s.score}%)")
        return 1
    else:
        print(f"✗ NOT FOUND: '{name}'")
        return 2


def main():
    if len(sys.argv) < 3:
        print("SQL Live Suggestion - Standalone CLI")
        print()
        print("Usage:")
        print("    python standalone/cli.py <scope> <name> [schema] [table]")
        print()
        print("Arguments:")
        print("    scope   : schema, table, or column")
        print("    name    : The name to validate")
        print("    schema  : (optional) Schema context for table/column")
        print("    table   : (optional) Table context for column")
        print()
        print("Examples:")
        print("    python standalone/cli.py schema public")
        print("    python standalone/cli.py table student public")
        print("    python standalone/cli.py table studnt public      # typo - shows suggestions")
        print("    python standalone/cli.py column email public student")
        print()
        print("Options:")
        print("    --env ENV       Environment: dev, qa, stage, prod (default: dev)")
        print("    --threshold N   Fuzzy match threshold 0-100 (default: 50)")
        print("    --pickle PATH   Custom pickle file path")
        sys.exit(1)
    
    # Parse arguments
    scope = sys.argv[1]
    name = sys.argv[2]
    schema = None
    table = None
    env = "dev"
    threshold = 50
    pickle_path = None
    
    # Parse optional positional arguments
    args = sys.argv[3:]
    positional_idx = 0
    i = 0
    while i < len(args):
        if args[i] == "--env" and i + 1 < len(args):
            env = args[i + 1]
            i += 2
        elif args[i] == "--threshold" and i + 1 < len(args):
            threshold = int(args[i + 1])
            i += 2
        elif args[i] == "--pickle" and i + 1 < len(args):
            pickle_path = args[i + 1]
            i += 2
        elif not args[i].startswith("--"):
            if positional_idx == 0:
                schema = args[i]
            elif positional_idx == 1:
                table = args[i]
            positional_idx += 1
            i += 1
        else:
            i += 1
    
    # Validate scope
    if scope not in ("schema", "table", "column"):
        print(f"Error: Invalid scope '{scope}'. Must be: schema, table, or column")
        sys.exit(1)
    
    # Determine pickle path
    if pickle_path is None:
        data_dir = project_root / "data"
        pickle_path = data_dir / f"metadata_{env}.pkl"
    else:
        pickle_path = Path(pickle_path)
    
    if not pickle_path.exists():
        print(f"Error: Pickle file not found: {pickle_path}")
        print(f"Available environments in data/:")
        data_dir = project_root / "data"
        if data_dir.exists():
            for f in data_dir.glob("metadata_*.pkl"):
                env_name = f.stem.replace("metadata_", "")
                print(f"    --env {env_name}")
        sys.exit(1)
    
    # Load cache
    cache = MetadataCache()
    try:
        cache.load_from_pickle(str(pickle_path))
    except Exception as e:
        print(f"Error loading pickle: {e}")
        sys.exit(1)
    
    # Show what we're validating
    print(f"Environment: {env}")
    print(f"Validating {scope}: '{name}'", end="")
    if schema:
        print(f" in schema '{schema}'", end="")
    if table:
        print(f", table '{table}'", end="")
    print()
    print()
    
    # Validate
    validator = Validator(cache, fuzzy_threshold=threshold)
    result = validator.validate(scope, name, schema=schema, table=table)
    
    # Print result
    exit_code = print_result(result, name)
    
    # Also print as dict for debugging
    print()
    print("Result:", result.to_dict())
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
