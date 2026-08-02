# Contributing

Thanks for helping improve Shadowing Player.

## Development setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
# Place libmpv-2.dll under vendor/libmpv/ (see vendor/libmpv/README.md)
.\.venv\Scripts\python.exe -m shadowing_player
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Pull requests

1. Keep changes focused (one feature or fix per PR).
2. Add or update tests when behavior changes.
3. Update `README.md` if user-facing behavior or shortcuts change.
4. Do not commit secrets, local media, models, `build/`, or `dist/`.

## Issue reports

Please include:

- Windows version and Python version
- Whether you used the source install or a folder package
- Steps to reproduce
- Expected vs actual behavior
