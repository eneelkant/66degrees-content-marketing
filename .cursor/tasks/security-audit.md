# Task: security-audit

## Objective
Scan the repository for committed secrets and unsafe credential handling.

## Required inputs
- None (repo-wide)

## Inspect
- `.env*`, configs, scripts, fixtures, docs
- `rg` for api keys / tokens / PATs / private keys
- `.gitignore` coverage for `.env`, `*secret*`, credential JSON

## Expected output
- Findings list (or clean bill)
- Remediations: env vars, `.env.example`, docs — **no new real secrets**

## Validation
- No live credentials in tree
- Logging redaction still covers sensitive keys
