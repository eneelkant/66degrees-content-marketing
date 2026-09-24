# Task: fix-test

## Objective
Make a failing test pass by fixing product code or correcting an invalid test — never by deleting coverage without cause.

## Required inputs
- Failing test node id / traceback

## Inspect
- Failing test and nearest implementation
- Whether the test assumed a populated `references.db` or live credentials

## Expected output
- Root-cause fix
- Deterministic test (fixtures/mocks)
- Suite green

## Validation
```bash
./scripts/test.sh
```
