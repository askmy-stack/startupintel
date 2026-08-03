# Security Policy

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

- Preferred: use GitHub's private vulnerability reporting for this repository
  (Security tab → **Report a vulnerability**).
- Alternative: email **kamineniabhinaysai@gmail.com** with a description of
  the issue, steps to reproduce, and its potential impact.

We aim to acknowledge reports within 7 days and to keep you updated as we
investigate and fix confirmed issues.

## Supported Versions

startupintel does not yet have tagged releases; security fixes are applied
to the `main` branch. Run the latest `main` to get fixes as soon as they
land.

## Authentication

- User-facing auth is JWT-based (HS256, signed with `API_SECRET_KEY`):
  short-lived access tokens plus refresh tokens (hashed with SHA-256 in the
  database) via `/auth/register`, `/auth/login`, `/auth/refresh`,
  `/auth/logout`, and `/auth/me`. Passwords are hashed with bcrypt.
  Refresh rotation requires a non-revoked token whose `expires_at` is still in
  the future; expired tokens return 401 and are not rotated.
- An `APIKey` model (`si_`-prefixed, SHA-256 hashed, with scopes and rate
  limits) exists in the schema, but no route currently authenticates via it —
  JWT bearer tokens are the active mechanism.
- **`/startup/*`, `/termsheet/*`, `/investor/*`, `/accelerator/*`,
  `/chat/*`, and `/bot/*` are not currently gated behind auth.** Only
  `/files/*`, `/feature-flags/*` (mutations require admin), and `/auth/me`
  require a JWT bearer token today. Treat any of those open routes as
  effectively public if you deploy this beyond local/trusted use, and open
  an issue/PR if you need them locked down for your deployment.
- `ENVIRONMENT != development` rejects insecure default values for
  `NEO4J_PASSWORD` and `API_SECRET_KEY` at startup — always set real secrets
  outside local development.

## API Keys and External Secrets

`.env.example` lists the external services this project can integrate with:
databases (Postgres, Neo4j, Redis, Kafka), LLM providers (Groq, or a local
Ollama instance), data sources (Crunchbase, GitHub, Twitter/X, Product Hunt,
SEC EDGAR, LinkedIn, App Store), and notifications (Slack, SendGrid, AWS).
Treat all of these as secrets: never commit real values, and rotate any key
you suspect may have leaked.

## Sensitive Data Handled

This project stores startup, investor, and accelerator data sourced from
public signals, along with data users provide directly:

- **Term sheets** (`TermSheetAnalysis.raw_text`) — the full text of uploaded
  term sheets, plus extracted clause scores and red flags.
- **User accounts** — email, bcrypt-hashed password, name, role, org
  membership.
- **Uploaded files** — org-scoped, with checksum and virus-scan status
  tracked in `UploadedFile`.
- **Bot outputs** — `StartupScore.llm_diagnosis` and `raw_signals` may
  contain LLM-generated text derived from ingested signals.

There are currently no GDPR/right-to-erasure endpoints. If you operate this
service on behalf of EU users or otherwise need erasure support, treat that
as a gap to close before processing regulated personal data.

## Cypher Query Safety

Bot classes (`startupintel/bots/*.py`) write scores into Neo4j via
`BaseBot.write_to_graph`. Property names derived from bot identifiers are
validated against a strict allowlist pattern before being used in a Cypher
query, since Neo4j has no parameterized syntax for property names — only
values use query parameters.
