# Optional AWS integration

PhishAware runs entirely locally by default — no AWS account or
credentials required. These files are here to show (and let you actually
exercise) the cloud-integration path a real security-awareness platform
would use in production:

- **`iam-policy-phishaware.json`** — least-privilege IAM policy for a role
  that can send campaign emails via **SES** and ship event logs to
  **CloudWatch Logs**. Attach to an IAM role (e.g. an EC2 instance role or
  a local `aws configure` profile), not to a long-lived access key if you
  can avoid it.

## To actually use it

1. Verify a sender identity in SES (or move your SES account out of the
   sandbox if sending to unverified recipients).
2. Create a CloudWatch Logs group, e.g. `/phishaware/events`.
3. Set in `.env`:
   ```
   MAIL_MODE=ses
   SES_SENDER=security-awareness@yourcompany.com
   SHIP_TO_CLOUDWATCH=true
   CLOUDWATCH_LOG_GROUP=/phishaware/events
   AWS_REGION=us-east-1
   ```
4. Make sure `boto3` can find credentials (env vars, `~/.aws/credentials`,
   or an instance/task role).

**Only point `MAIL_MODE=ses` at addresses you are explicitly authorized to
run a phishing-awareness test against** — e.g. your own org's employees,
with sign-off from security leadership/HR. The default `simulate` mode
(render-to-`.eml`, send nothing) is the right choice for a portfolio demo
or local development.