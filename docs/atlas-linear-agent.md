# Native Linear Atlas agent

This repository is allowlisted for the isolated native Linear Atlas engineering agent. Atlas works only within the delegated Linear issue and this repository's scoped checkout.

To delegate work, open or select a Linear issue for this repository and invoke the configured Atlas agent from the issue. Include the requested outcome and acceptance criteria so the native Agent Session can carry the task through verification.

For implementation tasks, Atlas creates an `atlas/` branch and commits the verified changes locally. Branches and pull requests are then published through the Atlas GitHub App, without using human GitHub credentials, and the resulting pull request is linked to the originating Linear Agent Session.
