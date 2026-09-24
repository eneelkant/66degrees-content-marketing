# Task: /social

## Objective
Generate platform-specific social posts from a source asset.

## Inputs
- Source asset JSON
- Platforms list (e.g. linkedin)

## MCP tools
- `generate_social_posts`
- `repurpose_content_asset`

## Expected output
- Assets per platform

## Validation
- Empty platforms must error clearly

## Safety
- Keep brand terminology; run `/brand-check` or QA before approval
