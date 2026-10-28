"""Count committed/demo JWT literals without printing credential material."""
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'api_service/tests/week7_8_acceptance_demo.py'
parser = argparse.ArgumentParser()
parser.add_argument('--baseline-ref', default='780af5375eec8aabc09ae3cebc84c967ce447b10')
args = parser.parse_args()
baseline = subprocess.run(['git', 'show', args.baseline_ref + ':' + TARGET], cwd=ROOT,
                          capture_output=True, text=True, encoding='utf-8', check=True).stdout
current = (ROOT / TARGET).read_text(encoding='utf-8')
pattern = re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}')
report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'path': TARGET,
          'baseline_ref': args.baseline_ref,
          'committed_head_embedded_jwt_count': len(pattern.findall(baseline)),
          'working_tree_embedded_jwt_count': len(pattern.findall(current)),
          'note': 'Only counts are saved. The historical Git commit still contains expired tokens.'}
destination = ROOT / 'docs/evidence/week7/secret-literal-check.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(destination, report['committed_head_embedded_jwt_count'], '->', report['working_tree_embedded_jwt_count'])
