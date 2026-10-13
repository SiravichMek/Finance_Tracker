# Finance Gmail Homelab — ingestion MVP

Starter for importing KBank and Krungsri transaction notification emails into PostgreSQL from a daily Kubernetes CronJob. The bank parsers are based on the two redacted sample messages supplied by the user.

## What it does
- Gmail API read-only scope
- Searches the last 14 days of candidate messages so a missed daily run can recover
- Parses KBank PromptPay transfer and Krungsri bill payment examples
- Stores THB amount, fee, timestamp (Asia/Bangkok), counterparty, bank transaction ID and category
- Uses Gmail message ID as a unique idempotency key
- Records each sync run and parse failures

## Limitations before production
- No dashboard/API yet; this is the ingestion foundation.
- Gmail OAuth consent/token bootstrap must be completed by the owner.
- HTML-only messages currently fail parsing; add a safe HTML-to-text fallback if real emails are HTML-only.
- Gmail query terms and parsers must be tested against real redacted samples from both banks.
- KBank person-to-person transfers are marked `Transfer / Review`, not automatically classified as consumption.
- Message-ID deduplication prevents re-importing the same email. If a bank sends duplicate notifications for the same underlying transaction in different emails, add a second deduplication rule based on bank transaction ID.
- The sample CronJob references a PostgreSQL secret and OAuth token secret that you must create. OAuth refresh is performed in memory; the long-lived refresh token remains read-only in the mounted Secret. Use an external secret manager or encrypted secret workflow for production.

## Run parser tests
```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## Gmail setup outline
1. Create a Google Cloud project and enable Gmail API.
2. Configure OAuth consent and create a Desktop OAuth client.
3. Authorize the Gmail account with `https://www.googleapis.com/auth/gmail.readonly` and obtain a refreshable `token.json`.
4. Keep OAuth client secrets and tokens out of Git. For Kubernetes, use a secret manager or a dedicated encrypted persistent volume with strict access controls for token refresh.

## Database
Create a PostgreSQL database and set `DATABASE_URL`, e.g. `postgresql://finance_app:REDACTED@postgres.finance.svc:5432/finance`. The worker creates its own tables at startup.

## Build
```bash
docker build -t YOUR_REGISTRY/finance-gmail-homelab:0.1.0 .
docker push YOUR_REGISTRY/finance-gmail-homelab:0.1.0
```

Update the image in `k8s/cronjob.yaml` before applying. Create the `finance-db` and `gmail-oauth-token` secrets securely before enabling the CronJob.
