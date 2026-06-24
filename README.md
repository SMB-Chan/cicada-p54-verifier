# cicada-p54-verifier

Independent reproducibility verifier for the Liber Primus p54 first-layer control scaffold.

---

## Scope and boundary

**This repository verifies one claim only:**

> The p54 first-layer control scaffold — its two-phase Atbash+prime operation system, EA boundary positions, A/B stream separation, and quarantined second-layer payloads — is fully reproducible from the raw rtkd transcription using the verifier script alone.

**This repository does not claim:**

- Any decipherment of p54's second-layer payload
- Any knowledge of the external running key required for the second layer
- Any relationship to prior circulating analysis materials (including files labelled v8.x)

The A-family payload (91 tokens) and B-family payload (57 tokens) produced here are **quarantined second-layer ciphertext**. They are made public so that independent researchers can confirm the control scaffold and use the frozen payloads as a correct oracle when searching for the second-layer key source.

---

## Quick start

```bash
python3 cicada_p54_minimal_public_verifier.py \
    liber-primus__transcription--master.txt \
    --outdir out \
    --shuffle 5000 \
    --seed 3301
```

Requires: Python 3.8+, no external dependencies. The transcription file is the rtkd/iddqd master transcription (SHA-256: `e21743ccd9a07f3845d52a329c61b9fa69e9ca6a44ee3ba0db8f28a0d7065004`).

Expected output: `Verdict: PASS`

---

## What the verifier checks

All 18 checks pass in a clean-room environment (input files: transcription + verifier script only).

### Structural facts (7/7)

| name | value |
|---|---|
| p54 token length | 232 |
| p55 token length | 76 |
| EA boundary positions | 48, 52, 54, 73, 135, 151, 211, 228 |
| A-face payload length | 91 tokens |
| B-face payload length | 57 tokens |
| terminal pidx at source₀=219 | 320 |
| compact scaffold score | 100/100 |

### Arithmetic coordinates (4 equations, all pass)

```
91  + 229 = 320   (A-face payload length + B-face pidx start − 1 + 1)
153 + 167 = 320
167 −  91 =  76   (= p55 token length)
229 − 153 =  76
```

These four equations converge on 320 and 76. The appearance of p55's token length (76) as a coordinate difference suggests a cross-page arithmetic relationship between p54 and p55, the nature of which is not yet understood.

---

## First-layer operation specification

The first layer applies two distinct operations depending on which face of p54 a source token belongs to.

### Phase switch

Source token at position 151 is an EA rune. It acts as a suppressed phase-switch marker: it is consumed but produces no output, and triggers the transition from A-face to B-face processing.

### A-face: Atbash then subtract

Applied to source positions 53–150 (98 source tokens; 9 are HOLD literals, 89 consume a prime index).

```
out_idx = (atbash(raw_idx) − (prime[pidx] − 1)) mod 29
```

- Starting prime index: **pidx = 157** (0-indexed; prime₁₅₇ = 929)
- HOLD rule: EA, X, and F tokens at specific positions are passed through as literals without consuming a prime index

### B-face: Atbash then add

Applied to source positions 152–228 (77 source tokens; 4 are DELETE-X, 73 consume a prime index).

```
out_idx = (atbash(raw_idx) + (prime[pidx] − 1)) mod 29
```

- Starting prime index: **pidx = 256** (0-indexed; prime₂₅₆ = 1621)
- DELETE-X rule: X tokens at positions 184, 191, 216, 226 are deleted from output and do **not** consume a prime index

### Atbash definition

```
atbash(idx) = 28 − idx      (mod-29 alphabet, 0-indexed)
```

### Note on pidx start values

The values 157 and 256 are reproduced here as observed. Their design rationale is not known. 157 is itself prime and is the 37th prime. 256 = 2⁸ and is not prime. Any claim about why these specific values were chosen should be treated as conjecture until independently supported.

### Note on IO/IA transcription ambiguity

The rtkd transcription uses both `IO` and `IA` for rune index 27. The verifier treats them as identical (both map to index 27). This is a known transcription ambiguity and does not affect the operation results.

---

## Frozen output streams

These values are frozen by the verifier and must match byte-for-byte in a clean-room run.

```
A_full (98 tokens):
DEATHEOWOXAEHUSOFDULALTHPEAARTROEORXTRIAUOJACSNGCAENGDPHACXAEIAHRBREADIAIJSGCDSCUDMESTXUTXDASSBEATHTHEXGAEIHINGIAJHFL

B_full (73 tokens):
IAPIAETHBTHFWEOWBLOYHPADSYPHNCJXLAENNGOEIAIBWJYIEAFEAJNUFWOECTHTHEREAXOEEODTHDEATHEOLDEATHETHYFHTH

control_scaffold (23 tokens):
DEATHBREADDTHDEATHEOLDEATHETHYFHTH

A_payload (91 tokens, second-layer ciphertext):
EOWOXAEHUSOFDULALTHPEAARTROEORXTRIAUOJACSNGCAENGDPHACXAEIAHRIAIJSGCDSCUDMESTXUTXDASSBEATHTHEXGAEIHINGIAJHFL

B_payload (57 tokens, second-layer ciphertext):
IAPIAETHBTHFWEOWBLOYHPADSYPHNCJXLAENNGOEIAIBWJYIEAFEAJNUFWOECTHTHEREAXOEEO
```

The control scaffold tokens (DEATH×3, BREAD×1) appear at fixed positions within the A and B full streams. They are the first-layer structural signal, not payload content.

---

## Clean-room CI

The `ci/` directory contains the audit harness and its frozen outputs. The CI run:

1. Copies only the transcription file and verifier script into an isolated workspace
2. Runs the verifier with no other inputs
3. Confirms all fact rows, exit code, and byte-level identity of deterministic outputs against frozen reference hashes

CI result: **18/18 checks pass, 6/6 machine-readable outputs byte-identical**.

SHA-256 of the verifier script: `0f0b59ea70af0107dde2a7a9905d8466c721b37b9256c86304f5e109565f545d`

---

## Open questions

The following are genuinely unsolved. No claim is made about their answers.

**Second-layer key source.** The A-payload (91 tokens) and B-payload (57 tokens) require an external running key — a specific text, in a specific edition, from a specific starting character position — to be deciphered. Exhaustive tests against candidate texts (Mabinogion, *Paradise Lost*, *His Dark Materials*, known LP plaintext pages) and multiple keystream types have returned noise. The problem is a lookup/identification challenge, not a classical cryptanalytic one.

**pidx start values.** Why A-face begins at prime index 157 and B-face at 256 is not known.

**B-face asymmetry.** The B-face has no HOLD rule and uses addition rather than subtraction. The reason for this asymmetry is not known.

**320 and 76 as design constants.** The four coordinate equations that converge on 320 and 76 (= p55 length) may encode a deliberate cross-page structure. The mechanism is unconfirmed.

---

## Repository structure

```
README.md                                    — this file
cicada_p54_minimal_public_verifier.py        — verifier (single script, no deps)
frozen/
  cicada_p54_minimal_public_verifier_facts.tsv
  cicada_p54_minimal_public_verifier_streams.tsv
  cicada_p54_minimal_public_verifier_trace.tsv
  cicada_p54_minimal_public_verifier_shuffle.tsv
  cicada_p54_minimal_public_verifier_hash_manifest.tsv
ci/
  cicada_p54_cleanroom_ci_audit.py
  cicada_p54_cleanroom_ci_report.txt
  cicada_p54_cleanroom_ci_checks.tsv
  cicada_p54_cleanroom_ci_hashes.tsv
  cicada_p54_cleanroom_ci_manifest.tsv
```

---

## Source

Transcription: [rtkd/iddqd](https://github.com/rtkd/iddqd) — `liber-primus__transcription--master.txt`

This repository makes no claim of affiliation with Cicada 3301.
