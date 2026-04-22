# Security

## Reporting a vulnerability
If you believe you found a security issue in Inspectra, do not open a public issue with exploit details.

Report it privately to the project maintainer first.

## Current security model
Inspectra is a self-hosted internal engineering tool. The current repository provides security minimum, not enterprise security.

Current constraints:
- no RBAC
- no SSO
- admin token is stored in browser localStorage for the current admin UI
- webhook protection uses a shared secret, not vendor-native signature validation

## Deployment guidance
- keep the admin UI and API behind trusted network boundaries
- change all default secrets before setting `APP_ENV=production`
- validate connector permissions and outbound access before using live data
