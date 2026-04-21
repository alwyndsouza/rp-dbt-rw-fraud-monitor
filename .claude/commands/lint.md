Run ruff lint and format checks across the entire producer package.

```bash
cd /home/user/fraud-detection-streaming/producers && ruff check . && ruff format --check .
```

If there are fixable issues, apply them automatically:
```bash
ruff check --fix . && ruff format .
```

Then re-run to confirm zero errors remain. Report a summary of what was fixed and what (if anything) requires manual attention.
