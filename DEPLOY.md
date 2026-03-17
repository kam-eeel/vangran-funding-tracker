# Vangran Funding Tracker — Deployment Guide

Complete guide to deploying the Vangran Funding Tracker on Cloudflare Workers + D1.

## Architecture

| Component | Cloudflare Service |
|---|---|
| API + Logic | Cloudflare Worker (Hono framework) |
| Database | Cloudflare D1 (SQLite-compatible) |
| Dashboard UI | Workers Static Assets (served from `public/`) |
| Daily Data Sync | Cron Trigger (scheduled handler) |

## Prerequisites

- **Node.js** v18+ ([nodejs.org](https://nodejs.org))
- **Cloudflare Account** ([dash.cloudflare.com](https://dash.cloudflare.com))
- **Wrangler CLI** (installed as dev dependency, or globally: `npm install -g wrangler`)

## Step 1: Install Dependencies

```bash
npm install
```

## Step 2: Authenticate with Cloudflare

```bash
npx wrangler login
```

This opens a browser window to authenticate with your Cloudflare account.

## Step 3: Create the D1 Database

```bash
npx wrangler d1 create vangran-funding
```

This outputs a database ID. Copy it.

## Step 4: Update `wrangler.toml`

Replace `YOUR_DATABASE_ID_HERE` with the actual database ID from Step 3:

```toml
[[d1_databases]]
binding = "DB"
database_name = "vangran-funding"
database_id = "abc123-your-actual-id-here"
```

## Step 5: Apply the Database Schema

**Remote (production):**
```bash
npx wrangler d1 execute vangran-funding --file=src/db/schema.sql
```

**Local (development):**
```bash
npx wrangler d1 execute vangran-funding --local --file=src/db/schema.sql
```

## Step 6: Local Development

```bash
npx wrangler dev
```

This starts a local server at `http://localhost:8787`. The dashboard and all API endpoints are available.

### Test the Scheduled Ingestion Locally

Start the dev server with `--test-scheduled`:
```bash
npx wrangler dev --test-scheduled
```

Then trigger the cron handler:
```bash
curl "http://localhost:8787/__scheduled?cron=0+6+*+*+*"
```

This fetches data from the Government of Canada Open Data API and populates your local D1 database. The first ingestion takes a minute or two.

## Step 7: Deploy to Production

```bash
npx wrangler deploy
```

This deploys the Worker, uploads static assets, and activates the cron trigger. Wrangler outputs the Worker URL (e.g., `https://vangran-funding-tracker.<your-subdomain>.workers.dev`).

## Step 8: Trigger Initial Data Ingestion

After the first deploy, the database is empty. Trigger the ingestion manually from the Cloudflare Dashboard:

1. Go to **Workers & Pages** → **vangran-funding-tracker** → **Triggers**
2. Click **Trigger Event** next to the cron trigger

Or use the Wrangler CLI to run a one-off scheduled event. The daily cron (`0 6 * * *`) will keep data updated automatically after this.

## Step 9: Verify

1. Visit your Worker URL — the dashboard should load with KPI cards and charts
2. Click "Explore" to verify the data table with filtering and pagination
3. Check the Cloudflare Dashboard → Workers → Logs to confirm the cron trigger runs

## Configuration Reference

### `wrangler.toml`

```toml
name = "vangran-funding-tracker"    # Worker name
main = "src/index.ts"               # Entry point

[assets]
directory = "./public"              # Static assets directory

[triggers]
crons = ["0 6 * * *"]              # Daily at 6:00 AM UTC

[[d1_databases]]
binding = "DB"                      # Binding name used in code
database_name = "vangran-funding"   # D1 database name
database_id = "your-id-here"       # D1 database ID
```

### Cron Schedule

The default schedule is `0 6 * * *` (daily at 6:00 AM UTC). To change it, edit the `crons` array in `wrangler.toml` and redeploy.

Examples:
- `0 */6 * * *` — every 6 hours
- `0 12 * * 1` — every Monday at noon UTC
- `0 0 1 * *` — first of every month

### Custom Domain

To serve the app on a custom domain:

1. Go to **Workers & Pages** → **vangran-funding-tracker** → **Settings** → **Domains & Routes**
2. Add a custom domain (must be on Cloudflare DNS)

## Useful Commands

```bash
# Check database record count
npx wrangler d1 execute vangran-funding --command="SELECT COUNT(*) FROM records"

# View recent logs
npx wrangler tail

# List all D1 databases
npx wrangler d1 list

# Delete and recreate database (if needed)
npx wrangler d1 delete vangran-funding
npx wrangler d1 create vangran-funding
```

## Data Source

All data is sourced from the [Government of Canada — Proactive Disclosure of Grants and Contributions](https://open.canada.ca/data/en/dataset/432527ab-7aac-45b5-81d6-7597107a7013).

The Worker fetches records for 10 Vancouver Granville postal code FSAs (V5V, V5W, V5X, V5Y, V5Z, V6H, V6J, V6L, V6M, V6P), filters for Vancouver recipients with agreements ending in 2021 or later, and stores them in D1.

## Costs

Cloudflare Workers Free Plan includes:
- 100,000 requests/day
- 10ms CPU time per request
- D1: 5M rows read, 100K rows written, 5GB storage per day
- Cron Triggers: included

This is well within free tier for this application.
