# Contributor Guide

This file outlines contributor rules.

## Scope

This repo contains the Lucas agent, dashboard, and Kubernetes manifests (examples).

Before working on a change, confirm which area is affected:
- `src/` - agent and dashboard application code
- `k8s/` - deployment manifests
- `scripts/` - helper scripts used in development and ops

## Getting Started

1. Read `README.md` for prerequisites and deployment basics.
2. Create a branch from `main` (or the default branch in your fork).
3. Keep changes focused and explain the motivation in the PR description.

## Development Notes

- Prefer small, reviewable PRs **( IMPORTANT !!! )**
- Keep configuration changes explicit
- Avoid committing secrets. Use sealed secrets (or External Secrets) as described in `README.md`.

## Tests and Checks

There is no standardized test or lint command documented yet.
- If you add tests, document how to run them in your PR.
- If you introduce a new toolchain (lint, format, CI), add instructions to `README.md`.

## PR Checklist

- The change is scoped and well described
- Any new configuration is documented
- Manifests in `k8s/` remain valid
- No secrets or credentials are included

## Reporting Issues

Use the issue templates in `.github/ISSUE_TEMPLATE/` and follow the prompts:

- **Bug report**: include expected vs actual behavior, steps to reproduce, and relevant logs/screenshots.
- **Feature request**: include the problem statement, proposed solution, scope, alternatives, and success criteria.
- **Quality of life (QoL)**: include the pain point, suggested improvement, scope, and any context.

## Contact

If you are unsure about a change, open a draft PR with context and questions.
