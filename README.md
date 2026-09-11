# 66degrees Content Marketing AI Agent

> An MCP-powered AI content marketing system for 66degrees — from campaign strategy and event briefs to content generation, QA, approval, and export.

## 🚀 Quick Setup — Start Here

### 1. Clone the repository

```bash
git clone https://github.com/eneelkant/66degrees-content-marketing.git
cd 66degrees-content-marketing
uv sync
pip install -e .
cp .env.example .env
uv run python -m clients.claude.server
