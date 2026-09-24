# Task: generate-blog

## Objective
Generate a blog content asset through the public API / MCP tool.

## Required inputs
- Topic / brief JSON
- Optional audience and CTA

## Inspect
- `generate_content_asset` with `asset_type` for blog strategies
- `core/generators/blog_strategist.py`, factory routing

## Expected output
- Asset with metadata/`asset_id`
- QA-ready draft status

## Validation
- `LLM_PROVIDER=mock`
- Follow with QA + optional optimize
