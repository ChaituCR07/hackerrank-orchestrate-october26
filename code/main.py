"""Main entry point for HackerRank Orchestrate - Ghost Data Still Exists.

Reads input deletion requests, audits personal-data deletion compliance,
and writes the required output.csv at the repository root.
"""

import sys
import os
import json
import argparse
import pandas as pd
from datetime import datetime

# Add repo root and code to sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from code.audit_engine import AuditEngine

def main():
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists - Deletion Audit Agent")
    parser.add_argument("--dataset_dir", default=os.path.join(repo_root, "dataset"), help="Path to dataset directory")
    parser.add_argument("--requests_csv", default=None, help="Path to deletion requests CSV (defaults to dataset/deletion_requests.csv)")
    parser.add_argument("--output_csv", default=os.path.join(repo_root, "output.csv"), help="Path to write output.csv")
    args = parser.parse_args()

    requests_path = args.requests_csv or os.path.join(args.dataset_dir, "deletion_requests.csv")
    
    print(f"Starting Ghost Data Audit Engine...")
    print(f"  Dataset directory: {args.dataset_dir}")
    print(f"  Requests file:     {requests_path}")
    print(f"  Target output:     {args.output_csv}")

    start_time = datetime.now()
    engine = AuditEngine(args.dataset_dir)
    df_reqs = pd.read_csv(requests_path)
    print(f"Loaded {len(df_reqs)} evaluation requests.")

    results = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for idx, row in df_reqs.iterrows():
        case_id = str(row['case_id']).strip()
        status, steps = engine.audit_case(row)
        status_counts[status] = status_counts.get(status, 0) + 1
        steps_json_str = json.dumps(steps, separators=(',', ':')) if steps else "[]"
        results.append({
            'case_id': case_id,
            'deletion_status': status,
            'steps_json': steps_json_str
        })

        if (idx + 1) % 100 == 0 or (idx + 1) == len(df_reqs):
            print(f"  Processed {idx + 1}/{len(df_reqs)} cases...")

    # Sort strictly by case_id
    out_df = pd.DataFrame(results)
    out_df = out_df.sort_values('case_id')

    # Write output CSV
    out_df.to_csv(args.output_csv, index=False, columns=['case_id', 'deletion_status', 'steps_json'])
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\nAudit Run Complete in {elapsed:.2f} seconds!")
    print(f"Summary of predictions ({len(out_df)} cases):")
    for k, v in status_counts.items():
        print(f"  {k}: {v} ({v/len(out_df)*100:.1f}%)")
    print(f"Output successfully written to: {args.output_csv}")

if __name__ == '__main__':
    main()
