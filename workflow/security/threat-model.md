# Threat model

Draft; refine per feature.

## In-app AI features
| Threat | Control | Test |
|---|---|---|
| Prompt injection via uploads, chat or feedback | Treat as untrusted data; separate from instructions; validate output | |
| Answer leakage through hints, sources or output before submission | Server checks submission status; answer keys excluded from AI context | |
| Cross-user or cross-course data access via retrieval | Retrieval filtered by authorised records server-side | |
| Unsafe rendered output (XSS) | Sanitise/escape AI output | |
| Quota exhaustion / abuse of SoC LLM | Per-user limits, input/output caps, backoff, saved generations | |

## Development process
| Threat | Control | Check |
|---|---|---|
| Secrets committed | `.env` ignored, `.env.example` only, secret scanning | |
| Vulnerable dependencies | `npm audit`, pip/uv audit in CI | |
| Over-permissioned CI or deploy tokens | Least-privilege GitHub Actions permissions, environment secrets | |
| Agent runs destructive or unreviewed changes | Human merge gate, read-only reviewers | |
