# Branch Protection Setup

GitHub branch protection is enforced in repository settings, not from tracked files. Use this checklist to configure the `main` branch so the repository rules match the committed CI/CD policy.

## Recommended Settings for `main`

- Require a pull request before merging
- Require approvals: at least 1
- Dismiss stale approvals when new commits are pushed
- Require review from Code Owners
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Restrict force pushes
- Do not allow branch deletion

## Required Status Checks

After the workflows run once in GitHub, require the checks created by:

- `CI`
- `Security and Dependency Audit`

If GitHub shows individual reusable-workflow job names instead of the top-level workflow names, require the checks corresponding to:

- `Backend Tests`
- `Frontend Quality`
- `Infrastructure Validation`
- `Workflow Lint`
- `Backend Dependency Audit`
- `Frontend Dependency Audit`

## Notes

- `Pre-Deploy Validation` is intended for `main` after merge and does not need to be a required pull request check.
- Review the exact displayed check names in GitHub Settings > Branches before saving the rule.
