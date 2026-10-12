# Repository governance

These instructions apply throughout the Music Sheet Transposer repository.

- Before implementation, read [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md) and [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md).
- Follow the authorization mode and scope supplied in each task. INVESTIGATE_ONLY permits inspection and evidence reporting, not source, test, configuration, or fixture edits.
- Identify the relevant constitution principles and acceptance requirements in each implementation report. Report evidence, failed or untested checks, remaining limitations, and acceptance status accurately.
- Preserve accepted features and all preexisting uncommitted work. Keep changes within the authorized scope.
- Do not implement speculative fixes. When evidence needed to proceed is insufficient, stop and report what is missing.
- Do not modify approved product principles without explicit Product Owner authorization. Do not independently redefine approved requirements.
- The Product Owner approves requirements and final functional acceptance. The Technical Lead owns architecture, scope, implementation specifications, and technical review. Codex executes authorized changes and reports evidence.
- A test PASS does not imply Product Owner acceptance. Use the acceptance gates and status vocabulary in ACCEPTANCE_CRITERIA.md; only explicit Product Owner approval permits ACCEPTED status for user-visible functionality.
- Do not automatically perform Git add, commit, push, reset, restore, clean, or stash. These operations require explicit task authorization.
