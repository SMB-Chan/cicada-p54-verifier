#!/usr/bin/env python3
"""
Clean-room CI audit for the Cicada p54 minimal public verifier.

Purpose:
  Verify that the public verifier can run from only two inputs:
    1) the raw Liber Primus transcription
    2) the minimal verifier script
  and that its key machine-readable outputs match the already-frozen reference outputs.

This is a reproducibility/audit harness. It does not decode p54 payload plaintext.
"""
from __future__ import annotations
import csv, hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from typing import Dict, List

ROOT = Path('/mnt/data')
RAW = ROOT / 'liber-primus__transcription--master.txt'
VERIFIER = ROOT / 'cicada_p54_minimal_public_verifier.py'
OUT_PREFIX = 'cicada_p54_cleanroom_ci'
CLEAN_ROOT = ROOT / 'cicada_p54_cleanroom_ci_workspace'
CLEAN_INPUT = CLEAN_ROOT / 'input'
CLEAN_OUT = CLEAN_ROOT / 'out'

REFERENCE_SUFFIXES = [
    '_facts.tsv',
    '_events.tsv',
    '_trace.tsv',
    '_streams.tsv',
    '_shuffle.tsv',
    '_summary.tsv',
]

KEY_FACTS_EXPECTED = {
    'p54_token_length': '232',
    'p55_token_length': '76',
    'EA_positions': '48,52,54,73,135,151,211,228',
    'A_payload_length': '91',
    'B_payload_length': '57',
    'terminal_pidx_source219': '320',
    'compact_score': '100',
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def write_tsv(path: Path, rows: List[Dict[str, object]], fields=None) -> None:
    if fields is None:
        fields=[]
        for r in rows:
            for k in r.keys():
                if k not in fields: fields.append(k)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter='\t', extrasaction='ignore')
        w.writeheader()
        for r in rows: w.writerow(r)

def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))

def read_facts(path: Path) -> Dict[str, Dict[str, str]]:
    return {r['name']: r for r in read_tsv(path)}

def main() -> int:
    checks: List[Dict[str, object]] = []
    def add_check(name, observed, expected, passed=None, detail=''):
        if passed is None:
            passed = (observed == expected)
        checks.append({'check': name, 'observed': observed, 'expected': expected, 'pass': bool(passed), 'detail': detail})

    add_check('raw_transcription_exists', RAW.exists(), True)
    add_check('minimal_verifier_exists', VERIFIER.exists(), True)
    if not RAW.exists() or not VERIFIER.exists():
        write_tsv(ROOT / f'{OUT_PREFIX}_checks.tsv', checks)
        return 2

    if CLEAN_ROOT.exists():
        shutil.rmtree(CLEAN_ROOT)
    CLEAN_INPUT.mkdir(parents=True)
    CLEAN_OUT.mkdir(parents=True)

    clean_raw = CLEAN_INPUT / RAW.name
    clean_verifier = CLEAN_INPUT / VERIFIER.name
    shutil.copy2(RAW, clean_raw)
    shutil.copy2(VERIFIER, clean_verifier)

    before_files = sorted(str(p.relative_to(CLEAN_ROOT)) for p in CLEAN_ROOT.rglob('*') if p.is_file())
    add_check('cleanroom_input_file_count_before_run', len(before_files), 2)
    add_check('cleanroom_contains_only_script_and_raw_before_run', ','.join(before_files), f'input/{VERIFIER.name},input/{RAW.name}')

    env = os.environ.copy()
    env['PYTHONPATH'] = ''
    cmd = [sys.executable, str(clean_verifier), str(clean_raw), '--outdir', str(CLEAN_OUT), '--shuffle', '5000', '--seed', '3301']
    proc = subprocess.run(cmd, text=True, capture_output=True, env=env, timeout=60)
    add_check('verifier_exit_code', proc.returncode, 0)
    add_check('stdout_contains_pass', 'Verdict: PASS' in proc.stdout, True)
    add_check('stderr_empty', proc.stderr.strip(), '')

    # Expected outputs from a successful run.
    produced = sorted(p.name for p in CLEAN_OUT.iterdir() if p.is_file())
    expected_outputs = sorted([
        'cicada_p54_minimal_public_verifier_report.txt',
        'cicada_p54_minimal_public_verifier_claim_card.md',
        'cicada_p54_minimal_public_verifier_facts.tsv',
        'cicada_p54_minimal_public_verifier_events.tsv',
        'cicada_p54_minimal_public_verifier_trace.tsv',
        'cicada_p54_minimal_public_verifier_streams.tsv',
        'cicada_p54_minimal_public_verifier_shuffle.tsv',
        'cicada_p54_minimal_public_verifier_summary.tsv',
        'cicada_p54_minimal_public_verifier_manifest.json',
    ])
    add_check('produced_output_count', len(produced), len(expected_outputs))
    add_check('produced_expected_outputs', ','.join(produced), ','.join(expected_outputs))

    fact_path = CLEAN_OUT / 'cicada_p54_minimal_public_verifier_facts.tsv'
    if fact_path.exists():
        facts = read_facts(fact_path)
        for k, exp in KEY_FACTS_EXPECTED.items():
            obs = facts.get(k, {}).get('observed', '<missing>')
            add_check(f'fact_{k}', obs, exp)
        failed_facts = [k for k, r in facts.items() if str(r.get('pass')).lower() not in ('true','1','yes')]
        add_check('all_fact_rows_pass', len(failed_facts), 0, detail=','.join(failed_facts))
    else:
        add_check('facts_file_exists', False, True)

    # Compare clean-room outputs with frozen reference outputs for deterministic machine-readable files.
    comparisons: List[Dict[str, object]] = []
    for suffix in REFERENCE_SUFFIXES:
        ref = ROOT / f'cicada_p54_minimal_public_verifier{suffix}'
        new = CLEAN_OUT / f'cicada_p54_minimal_public_verifier{suffix}'
        row = {
            'file': f'cicada_p54_minimal_public_verifier{suffix}',
            'reference_exists': ref.exists(),
            'cleanroom_exists': new.exists(),
            'reference_sha256': sha256(ref) if ref.exists() else '',
            'cleanroom_sha256': sha256(new) if new.exists() else '',
            'byte_identical': False,
        }
        row['byte_identical'] = row['reference_sha256'] == row['cleanroom_sha256'] and ref.exists() and new.exists()
        comparisons.append(row)
    add_check('machine_readable_outputs_byte_identical', sum(1 for r in comparisons if r['byte_identical']), len(comparisons))

    # Hash all clean-room outputs plus inputs.
    hash_rows: List[Dict[str, object]] = []
    for p in sorted([clean_raw, clean_verifier] + list(CLEAN_OUT.glob('*'))):
        hash_rows.append({
            'role': 'input' if p.parent == CLEAN_INPUT else 'output',
            'path': str(p.relative_to(CLEAN_ROOT)),
            'bytes': p.stat().st_size,
            'sha256': sha256(p),
        })

    # Write audit outputs in /mnt/data.
    write_tsv(ROOT / f'{OUT_PREFIX}_checks.tsv', checks)
    write_tsv(ROOT / f'{OUT_PREFIX}_comparison.tsv', comparisons)
    write_tsv(ROOT / f'{OUT_PREFIX}_hashes.tsv', hash_rows)
    (ROOT / f'{OUT_PREFIX}_stdout.txt').write_text(proc.stdout, encoding='utf-8')
    (ROOT / f'{OUT_PREFIX}_stderr.txt').write_text(proc.stderr, encoding='utf-8')

    passed = all(bool(c['pass']) for c in checks)
    report = f"""Cicada p54 clean-room CI audit
================================

Verdict: {'PASS' if passed else 'FAIL'}

Scope:
- Copy only the raw Liber Primus transcription and the minimal public verifier into an isolated workspace.
- Run the verifier with no derived input files.
- Confirm fact rows, deterministic outputs, and byte-level agreement with the frozen reference outputs.

Clean-room workspace:
- {CLEAN_ROOT}

Core results:
- verifier exit code: {proc.returncode}
- fact checks: {sum(1 for c in checks if c['check'].startswith('fact_') and c['pass'])}/{sum(1 for c in checks if c['check'].startswith('fact_'))}
- all machine-readable deterministic outputs byte-identical: {sum(1 for r in comparisons if r['byte_identical'])}/{len(comparisons)}
- clean-room input files before run: {len(before_files)}

Boundary statement:
This CI audit strengthens reproducibility of the p54 control-layer and payload-quarantine claims only.
It does not decode the A-family or B-family second-layer payloads.
"""
    (ROOT / f'{OUT_PREFIX}_report.txt').write_text(report, encoding='utf-8')

    claim = """# Clean-room CI claim card

**Supported claim:** the minimal public verifier runs in a clean workspace using only the raw Liber Primus transcription and the verifier script, and reproduces the frozen machine-readable p54 control-layer outputs byte-for-byte.

**Not claimed:** this is not a plaintext solution of p54. The A-family and B-family payloads remain quarantined as undecoded second-layer ciphertext.
"""
    (ROOT / f'{OUT_PREFIX}_claim_card.md').write_text(claim, encoding='utf-8')

    manifest_rows = []
    out_files = [
        f'{OUT_PREFIX}_report.txt', f'{OUT_PREFIX}_claim_card.md', f'{OUT_PREFIX}_checks.tsv',
        f'{OUT_PREFIX}_comparison.tsv', f'{OUT_PREFIX}_hashes.tsv', f'{OUT_PREFIX}_stdout.txt',
        f'{OUT_PREFIX}_stderr.txt'
    ]
    for name in out_files:
        p = ROOT / name
        manifest_rows.append({'file': name, 'bytes': p.stat().st_size, 'sha256': sha256(p)})
    write_tsv(ROOT / f'{OUT_PREFIX}_manifest.tsv', manifest_rows)

    # Package outputs.
    zip_path = ROOT / f'{OUT_PREFIX}_bundle.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name in out_files + [f'{OUT_PREFIX}_manifest.tsv']:
            z.write(ROOT / name, arcname=name)
        # Include the clean-room verifier inputs and generated outputs under a namespace.
        for p in sorted(CLEAN_ROOT.rglob('*')):
            if p.is_file():
                z.write(p, arcname=str(Path('cleanroom_workspace') / p.relative_to(CLEAN_ROOT)))
    print(report)
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
