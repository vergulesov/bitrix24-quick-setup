# Bitrix24 Quick Setup

Quick setup of a Bitrix24 portal through REST API.

The project is intentionally small: automate the repetitive portal configuration that is useful for a demo, test assignment, or a fresh sandbox.

## What it will configure

- REST connectivity check
- company / department structure where API access allows
- CRM deal pipeline
- pipeline stages
- selected CRM fields
- synthetic demo candidates

Real credentials and personal data never belong in the repository.

## Setup

1. Copy `.env.example` to `.env`.
2. Put your Bitrix24 incoming webhook URL into `BITRIX_WEBHOOK`.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Check the connection:

```bash
python main.py check
```

5. Run setup:

```bash
python main.py setup
```

6. Seed demo data:

```bash
python main.py demo
```

## Safety

- `.env` is ignored by Git.
- Only synthetic demo data should be committed.
- The setup script is designed to be re-runnable where practical.
