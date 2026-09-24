# Task: export-campaign

## Objective
Export an approved campaign kit to JSON, DOCX, or XLSX.

## Required inputs
- `kit_id` present in session store
- Explicit prior `approve_campaign_kit`
- `export_format`: json | docx | xlsx

## Inspect
- `core/approval/gate.py`
- `exporters/campaign.py`
- `clients.public_api.export_campaign_kit`

## Expected output
- File path under exports directory
- `PermissionError` if not approved

## Validation
- Prove blocked-without-approval and success-after-approval
