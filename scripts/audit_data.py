#!/usr/bin/env python3
"""Audit supplied CSV consistency and static T1 retrieval against T2 labels."""
from pathlib import Path
import argparse,json
from cad_sim.data_audit import audit_data

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../data'))
    parser.add_argument('--output-dir',type=Path,default=Path('results/data_audit'))
    args=parser.parse_args()
    print(json.dumps(audit_data(args.data_dir,args.output_dir),indent=2))
