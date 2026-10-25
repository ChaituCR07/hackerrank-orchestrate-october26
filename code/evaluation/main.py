"""Evaluation harness for HackerRank Orchestrate - Ghost Data Still Exists.

Computes case-level, row-level, field-level, and sequence accuracy against ground truth,
evaluates edge cases and custom cases, and generates the evaluation report.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Tuple
import pandas as pd

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from code.audit_engine import AuditEngine

def compare_step(pred: Dict[str, Any], exp: Dict[str, Any]) -> Dict[str, bool]:
    fields = ['step_no', 'phase', 'system_id', 'resource_id', 'operation', 'state', 'evidence_id']
    return {f: str(pred.get(f, '')).strip() == str(exp.get(f, '')).strip() for f in fields}

def evaluate(pred_df: pd.DataFrame, ground_truth_df: pd.DataFrame) -> Dict[str, Any]:
    pred_map = pred_df.set_index('case_id')
    gt_map = ground_truth_df.set_index('case_id')
    
    total_cases = len(gt_map)
    status_matches = 0
    row_matches = 0
    total_expected_steps = 0
    matched_steps = 0
    
    field_counts = {f: 0 for f in ['step_no', 'phase', 'system_id', 'resource_id', 'operation', 'state', 'evidence_id']}
    field_totals = 0
    
    case_results = []

    for cid, exp_row in gt_map.iterrows():
        exp_status = exp_row['deletion_status']
        exp_steps = json.loads(exp_row['steps_json']) if pd.notna(exp_row['steps_json']) else []
        
        if cid not in pred_map.index:
            case_results.append({
                'case_id': cid,
                'status_match': False,
                'row_match': False,
                'step_accuracy': 0.0,
                'pred_status': 'MISSING',
                'exp_status': exp_status,
                'note': 'Case missing from predictions'
            })
            continue

        pred_row = pred_map.loc[cid]
        pred_status = pred_row['deletion_status']
        pred_steps = json.loads(pred_row['steps_json']) if pd.notna(pred_row['steps_json']) else []

        status_ok = (pred_status == exp_status)
        if status_ok:
            status_matches += 1

        total_expected_steps += len(exp_steps)
        step_len_ok = (len(pred_steps) == len(exp_steps))
        
        step_matches_in_case = 0
        min_len = min(len(pred_steps), len(exp_steps))
        for i in range(min_len):
            field_comp = compare_step(pred_steps[i], exp_steps[i])
            all_fields_ok = all(field_comp.values())
            if all_fields_ok:
                step_matches_in_case += 1
                matched_steps += 1
            for f, ok in field_comp.items():
                if ok:
                    field_counts[f] += 1
            field_totals += 1

        # Excess expected steps count toward field_totals as failures
        if len(exp_steps) > min_len:
            field_totals += (len(exp_steps) - min_len)

        row_ok = status_ok and step_len_ok and (step_matches_in_case == len(exp_steps))
        if row_ok:
            row_matches += 1

        case_results.append({
            'case_id': cid,
            'status_match': status_ok,
            'row_match': row_ok,
            'pred_len': len(pred_steps),
            'exp_len': len(exp_steps),
            'pred_status': pred_status,
            'exp_status': exp_status
        })

    status_acc = status_matches / total_cases if total_cases > 0 else 0.0
    row_acc = row_matches / total_cases if total_cases > 0 else 0.0
    step_acc = matched_steps / total_expected_steps if total_expected_steps > 0 else 0.0
    field_acc = {f: (field_counts[f] / field_totals) if field_totals > 0 else 0.0 for f in field_counts}
    overall_field_acc = (sum(field_counts.values()) / (field_totals * len(field_counts))) if field_totals > 0 else 0.0

    return {
        'total_cases': total_cases,
        'status_matches': status_matches,
        'status_accuracy': status_acc,
        'row_matches': row_matches,
        'row_accuracy': row_acc,
        'total_expected_steps': total_expected_steps,
        'matched_steps': matched_steps,
        'step_accuracy': step_acc,
        'field_accuracy': field_acc,
        'overall_field_accuracy': overall_field_acc,
        'case_results': case_results
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Ghost Data Deletion Engine")
    parser.add_argument("--dataset_dir", default=os.path.join(repo_root, "dataset"))
    parser.add_argument("--sample_requests", default=os.path.join(repo_root, "dataset", "sample_deletion_requests.csv"))
    parser.add_argument("--sample_gt", default=os.path.join(repo_root, "dataset", "sample_output.csv"))
    args = parser.parse_args()

    print(f"Initializing AuditEngine with dataset from {args.dataset_dir}...")
    engine = AuditEngine(args.dataset_dir)
    
    print(f"Loading sample evaluation requests from {args.sample_requests}...")
    reqs_df = pd.read_csv(args.sample_requests)
    
    print(f"Running inference on {len(reqs_df)} sample requests...")
    pred_rows = []
    for _, row in reqs_df.iterrows():
        cid = str(row['case_id']).strip()
        status, steps = engine.audit_case(row)
        pred_rows.append({
            'case_id': cid,
            'deletion_status': status,
            'steps_json': json.dumps(steps, separators=(',', ':')) if steps else "[]"
        })
    pred_df = pd.DataFrame(pred_rows)

    print(f"Loading ground truth from {args.sample_gt}...")
    gt_df = pd.read_csv(args.sample_gt)

    metrics = evaluate(pred_df, gt_df)

    print("\n" + "=" * 55)
    print("        SAMPLE DATASET EVALUATION METRICS")
    print("=" * 55)
    print(f"Total Evaluated Cases:   {metrics['total_cases']}")
    print(f"Case Status Accuracy:    {metrics['status_matches']}/{metrics['total_cases']} ({metrics['status_accuracy']*100:.2f}%)")
    print(f"Exact Row Accuracy:      {metrics['row_matches']}/{metrics['total_cases']} ({metrics['row_accuracy']*100:.2f}%)")
    print(f"Step Sequence Accuracy:  {metrics['matched_steps']}/{metrics['total_expected_steps']} ({metrics['step_accuracy']*100:.2f}%)")
    print(f"Overall Field Accuracy:  {metrics['overall_field_accuracy']*100:.2f}%")
    print("\nPer-Field Accuracy Breakdown:")
    for f, acc in metrics['field_accuracy'].items():
        print(f"  - {f:15s}: {acc*100:.2f}%")
    print("=" * 55)

    return metrics

if __name__ == '__main__':
    main()
