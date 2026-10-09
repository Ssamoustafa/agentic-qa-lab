# Contributing

Use feature branches and keep commits focused.

Before opening a PR:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

`pytest` enforces the repository coverage threshold configured in `pyproject.toml`.

Architecture rules:
1. Domain code must not import browser, AI-provider, filesystem, or CI SDKs.
2. Agent output is untrusted until validated by domain policy.
3. New executable actions require domain, policy, executor, and test changes.
4. Never solve flaky behavior with blanket retries.
5. Security controls must be executable and tested, not only documented.
6. Keep each change on a feature branch with a focused conventional commit.
