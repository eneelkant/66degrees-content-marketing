# Task: generate-social-content

## Objective
Produce platform-specific social posts from a source asset.

## Required inputs
- Source asset JSON
- Platforms list (e.g. linkedin, x)

## Inspect
- `clients.public_api.generate_social_posts`
- `core/optimization/repurposer.py`

## Expected output
- One asset per platform under `assets`

## Validation
- Empty platforms must error clearly
- Mock provider only in automated runs
