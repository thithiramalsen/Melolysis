# Melolysis

Melody analysis and generation pipeline (vocal-focused).

## Quick start (Windows PowerShell)

```powershell
cd /d d:\VSCode\GitHub\Melolysis
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Quick start (macOS / Linux)

```bash
cd /path/to/Melolysis
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Notes

- The repository ignores `.venv/` and `data/` by default via `.gitignore`.
- If you want to track example audio, remove `data/` from `.gitignore`.
