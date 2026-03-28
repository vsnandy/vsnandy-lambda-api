# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backend API for vsnandy.github.io — a serverless AWS Lambda function that routes requests to NCAA, ESPN, and Pick Poolr (fantasy betting) handlers. No web framework is used; routing is done manually in `handler.py`.

## Local Development

**Start local API (requires AWS SAM CLI):**
```bash
sam local start-api
```

**Start LocalStack (local AWS emulation):**
```bash
docker-compose up
```

LocalStack emulates DynamoDB, Lambda, IAM, and CloudWatch on ports 4566–4593.

**Invoke a specific event locally:**
```bash
sam local invoke -e events/get-nfl-athletes.json
```

There are no automated tests. The `events/` directory contains sample Lambda event payloads for manual local invocation.

## Deployment

Deployment is fully managed via Terraform. GitHub Actions (`.github/workflows/`) auto-apply on push to `main`. Required Terraform variables are injected from GitHub secrets (`TF_VAR_*`).

**Manually plan/apply:**
```bash
terraform init
terraform plan
terraform apply
```

## Architecture

### Request Flow
```
API Gateway V2 (HTTP) → Cognito JWT Authorizer → Lambda → handler.py → api/*.py → DynamoDB / External APIs
```

### Routing (`src/handler.py`)
The handler uses a `ROUTES` dict mapping `(method, path_pattern)` to handler functions, with a custom `match_route()` for path parameter extraction. All responses go through `build_response()` in `helper.py`, which sets CORS headers allowing `https://vsnandy.github.io` and `http://localhost:3000`.

### API Modules (`src/api/`)
- **`ncaa.py`** — NCAA sports data + WAPIT (March Madness fantasy draft). Hits `data.ncaa.com/casablanca` for game data and `sdataprod.ncaa.com` (GraphQL) for live MM stats. Reads/writes `wapit_draft` DynamoDB table; queries Cognito for league members.
- **`espn.py`** — ESPN sports data (college football focus). Wraps ESPN Core, Site, and CDN APIs.
- **`pick_poolr.py`** — CRUD for `pick_poolr_bets` DynamoDB table. PK: `BETTOR#{bettor}`, SK: `WEEK#{week}`.

### DynamoDB Tables
| Table | PK | SK | Purpose |
|---|---|---|---|
| `vsnandy_bets` | Bettor | Week | Legacy vsnandy league bets |
| `wapit_draft` | LeagueID | PickNumber | WAPIT March Madness draft picks |
| `pick_poolr_bets` | `BETTOR#{bettor}` | `WEEK#{week}` | Pick Poolr betting records |

### Infrastructure (`main.tf`)
Defines all AWS resources: Lambda functions, API Gateway V2, DynamoDB tables, Cognito User Pool (`vsnandy-user-pool-v2`), and IAM roles. Terraform state is stored in S3 bucket `vsnandy-tfstate`.

### Authorizer (`src_auth/handler.py`)
Currently a no-op placeholder that returns `{statusCode: 204}`. JWT validation is delegated to API Gateway's native Cognito integration.

## Adding New Endpoints

1. Add a handler function in the appropriate `src/api/*.py` module
2. Add the route to the `ROUTES` dict in `src/handler.py`
3. Add the SAM event in `template.yaml` (for local testing)
4. Add the API Gateway route in `main.tf` if it needs explicit Terraform management
