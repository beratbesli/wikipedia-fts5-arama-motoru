# Security Policy

## Scope

This project is a local Python/SQLite search application. The supported
security surface is the code on `main`, the published package, and the latest
tagged release. It does not run a hosted service or accept remote requests.

## Reporting a vulnerability

Please report security issues privately through GitHub's **Report a
vulnerability** flow on this repository. Do not attach private datasets,
database files, or exploit details to a public issue. If private reporting is
unavailable, share only a non-sensitive summary publicly and request a private
channel.

Include the affected commit or release, Python/SQLite versions, a minimal
reproduction, and whether the issue came from the application or an external
dataset. Dataset provenance or a malicious input that changes query behavior
is in scope; do not submit personal data.

## Response

Reports are investigated against the current `main` branch and coordinated
with the reporter before public disclosure. Published dataset checksums and
provenance remain separate from application security claims.
