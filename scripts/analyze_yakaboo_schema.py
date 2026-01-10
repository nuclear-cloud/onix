#!/usr/bin/env python3
"""
Yakaboo JSON Schema Analyzer
=============================

Streaming parser that:
1. Processes large JSONL files chunk-by-chunk (no full file load)
2. Extracts all unique paths (leaf nodes + nested structures)
3. Tracks data types, frequencies, nesting depth
4. Outputs complete schema tree and frequency analysis

Features:
- Handles 10GB+ files efficiently
- Optional sampling (every Nth record)
- Frequency analysis (mandatory vs optional fields)
- JSON Schema Draft 7 output
- Visual tree representation

Run:
  python scripts/analyze_yakaboo_schema.py --file data/yakaboo_complete_final.jsonl --sample 100
  python scripts/analyze_yakaboo_schema.py --file data/yakaboo_complete_final.jsonl --limit 10000
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Set, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SchemaAnalyzer:
    """Analyzes JSON structure and generates schema."""
    
    def __init__(self):
        self.paths: Dict[str, Dict[str, Any]] = {}  # path -> {types, count, examples}
        self.total_records = 0
        self.records_with_path: Dict[str, int] = defaultdict(int)  # path -> count
        self.type_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.max_depth = 0
        self.array_items: Dict[str, Set[str]] = defaultdict(set)  # array paths -> item types
    
    def extract_paths(self, obj: Any, path: str = "root", depth: int = 0) -> None:
        """
        Extract all paths from a JSON object.
        
        Args:
            obj: The object to analyze
            path: Current path (dot notation)
            depth: Current nesting depth
        """
        self.max_depth = max(self.max_depth, depth)
        
        if obj is None:
            self._record_path(path, "null")
            
        elif isinstance(obj, bool):
            self._record_path(path, "boolean")
            
        elif isinstance(obj, (int, float)):
            self._record_path(path, "number")
            
        elif isinstance(obj, str):
            self._record_path(path, "string")
            
        elif isinstance(obj, list):
            self._record_path(path, "array")
            
            # Analyze array items
            if obj:
                for idx, item in enumerate(obj[:5]):  # Sample first 5 items
                    item_type = self._get_type(item)
                    self.array_items[path].add(item_type)
                    
                    # If item is object, analyze its structure
                    if isinstance(item, dict):
                        for key, val in item.items():
                            self.extract_paths(val, f"{path}[{idx}].{key}", depth + 1)
                            
        elif isinstance(obj, dict):
            self._record_path(path, "object")
            
            # Recursively analyze object fields
            for key, val in obj.items():
                new_path = f"{path}.{key}" if path != "root" else f"{path}.{key}"
                self.extract_paths(val, new_path, depth + 1)
    
    def _record_path(self, path: str, data_type: str) -> None:
        """Record a path and its type."""
        if path not in self.paths:
            self.paths[path] = {
                'types': set(),
                'count': 0,
                'examples': []
            }
        
        self.paths[path]['types'].add(data_type)
        self.paths[path]['count'] += 1
        self.type_counts[path][data_type] += 1
    
    def _get_type(self, obj: Any) -> str:
        """Get JSON type of an object."""
        if obj is None:
            return "null"
        elif isinstance(obj, bool):
            return "boolean"
        elif isinstance(obj, (int, float)):
            return "number"
        elif isinstance(obj, str):
            return "string"
        elif isinstance(obj, list):
            return "array"
        elif isinstance(obj, dict):
            return "object"
        return "unknown"
    
    def record_object_analyzed(self) -> None:
        """Call after processing each object to track mandatory fields."""
        self.total_records += 1
        for path in self.paths:
            self.records_with_path[path] += 1
    
    def get_field_prevalence(self, path: str) -> float:
        """Get percentage of records containing this field."""
        if self.total_records == 0:
            return 0.0
        return (self.records_with_path[path] / self.total_records) * 100
    
    def generate_tree(self, prefix: str = "") -> List[str]:
        """Generate visual tree representation of schema."""
        lines = []
        sorted_paths = sorted(self.paths.keys())
        
        for i, path in enumerate(sorted_paths):
            info = self.paths[path]
            types = ', '.join(sorted(info['types']))
            prevalence = self.get_field_prevalence(path)
            count = info['count']
            
            # Determine if mandatory (>95%), common (>50%), or optional
            if prevalence >= 95:
                freq_marker = "⭐"  # Mandatory
            elif prevalence >= 50:
                freq_marker = "🔶"  # Common
            else:
                freq_marker = "🔹"  # Optional
            
            # Visual tree structure
            is_last = i == len(sorted_paths) - 1
            connector = "└── " if is_last else "├── "
            
            # Extract field name
            field_name = path.split('.')[-1] if '.' in path else path
            
            lines.append(
                f"{connector}{freq_marker} {field_name:<40} "
                f"[{types:<20}] "
                f"({prevalence:5.1f}% / {count:,})"
            )
        
        return lines
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema Draft 7."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Yakaboo Product Schema",
            "type": "object",
            "properties": {},
            "required": [],
        }
        
        # Group paths by top-level fields
        top_level_fields = defaultdict(dict)
        
        for path, info in self.paths.items():
            if path == "root":
                continue
            
            parts = path.split('.')
            if len(parts) >= 2:
                top_field = parts[1]
                
                if top_field not in schema["properties"]:
                    schema["properties"][top_field] = {
                        "type": list(info['types'])[0] if info['types'] else "string"
                    }
                
                # Mark as required if >95% prevalence
                if self.get_field_prevalence(path) >= 95 and top_field not in schema["required"]:
                    schema["required"].append(top_field)
        
        return schema
    
    def generate_report(self) -> str:
        """Generate human-readable analysis report."""
        lines = [
            "=" * 100,
            "YAKABOO JSON SCHEMA ANALYSIS",
            "=" * 100,
            f"Total records analyzed: {self.total_records:,}",
            f"Unique paths found: {len(self.paths):,}",
            f"Maximum nesting depth: {self.max_depth}",
            "",
            "LEGEND:",
            "  ⭐ Mandatory (present in 95%+ of records)",
            "  🔶 Common (present in 50-95% of records)",
            "  🔹 Optional (present in <50% of records)",
            "",
            "FIELD TREE:",
            "-" * 100,
        ]
        
        lines.extend(self.generate_tree())
        
        # Detailed field info
        lines.extend([
            "",
            "=" * 100,
            "DETAILED FIELD ANALYSIS",
            "=" * 100,
        ])
        
        for path in sorted(self.paths.keys()):
            info = self.paths[path]
            types = sorted(info['types'])
            prevalence = self.get_field_prevalence(path)
            
            lines.extend([
                f"\nPath: {path}",
                f"  Types: {', '.join(types)}",
                f"  Occurrences: {info['count']:,} / {self.total_records:,} ({prevalence:.1f}%)",
            ])
            
            # Type distribution
            if len(self.type_counts[path]) > 1:
                lines.append("  Type distribution:")
                for dtype, count in sorted(self.type_counts[path].items(), key=lambda x: x[1], reverse=True):
                    lines.append(f"    - {dtype}: {count:,}")
            
            # Array item types
            if path in self.array_items and self.array_items[path]:
                lines.append(f"  Array item types: {', '.join(sorted(self.array_items[path]))}")
        
        return "\n".join(lines)


def process_jsonl(
    file_path: Path,
    analyzer: SchemaAnalyzer,
    limit: Optional[int] = None,
    sample: Optional[int] = None,
    verbose: bool = False
) -> int:
    """
    Stream process JSONL file without loading entire content.
    
    Args:
        file_path: Path to JSONL file
        analyzer: SchemaAnalyzer instance
        limit: Max records to process (None = all)
        sample: Process every Nth record (None = all)
        verbose: Print progress
    
    Returns:
        Number of records processed
    """
    processed = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Apply limit
            if limit and processed >= limit:
                break
            
            # Apply sampling
            if sample and (line_num % sample) != 0:
                continue
            
            try:
                obj = json.loads(line)
                analyzer.extract_paths(obj)
                analyzer.record_object_analyzed()
                processed += 1
                
                # Progress output
                if verbose and processed % 1000 == 0:
                    print(f"  Processed: {processed:,} records ({line_num:,} lines)")
                    
            except json.JSONDecodeError as e:
                if verbose:
                    print(f"  ⚠️  Line {line_num}: JSON parse error - {str(e)[:50]}")
                continue
    
    return processed


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Yakaboo JSON schema from streaming JSONL file"
    )
    parser.add_argument(
        '--file',
        default='data/yakaboo_complete_final.jsonl',
        help='Path to JSONL file'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Max records to analyze (None = all)'
    )
    parser.add_argument(
        '--sample',
        type=int,
        default=None,
        help='Sample every Nth record (None = all)'
    )
    parser.add_argument(
        '--output',
        default='docs/yakaboo_schema.json',
        help='Output JSON schema file'
    )
    parser.add_argument(
        '--report',
        default='docs/yakaboo_schema_report.txt',
        help='Output analysis report file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print progress'
    )
    
    args = parser.parse_args()
    
    path = Path(args.file)
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    
    print(f"🚀 Starting schema analysis")
    print(f"📁 File: {path}")
    print(f"📊 Size: {path.stat().st_size / (1024**3):.2f} GB")
    if args.limit:
        print(f"📈 Limit: {args.limit:,} records")
    if args.sample:
        print(f"🎲 Sampling: every {args.sample}th record")
    print()
    
    analyzer = SchemaAnalyzer()
    
    print("⏳ Processing file...")
    processed = process_jsonl(
        path,
        analyzer,
        limit=args.limit,
        sample=args.sample,
        verbose=args.verbose
    )
    
    print(f"✅ Processed: {processed:,} records")
    print()
    
    # Generate outputs
    print("📝 Generating report...")
    report = analyzer.generate_report()
    
    print("🔄 Generating JSON schema...")
    schema = analyzer.to_json_schema()
    
    # Save outputs
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, default=str)
    print(f"✅ Schema saved: {output_path}")
    
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ Report saved: {report_path}")
    
    # Print summary
    print("\n" + report)
    print("\n" + "=" * 100)
    print("💾 Files saved. Schema and report ready for analysis.")


if __name__ == '__main__':
    main()
