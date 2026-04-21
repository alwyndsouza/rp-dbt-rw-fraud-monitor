Run the full pytest suite for the producer.

```bash
cd /home/user/fraud-detection-streaming/producers && python -m pytest tests/ -v --tb=short
```

After running, report:
- Total tests passed / failed
- Any failures with the exact assertion message and file:line
- Whether `ruff check .` is also clean

If any tests fail, diagnose the root cause and propose a fix. Do not mark the task complete until all 75 tests pass.
