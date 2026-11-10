# DeskCompy

A tiny desk companion that watches your rhythm (never your words) and keeps
you company while you work, study, or play.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

No console window:

```bash
launch.bat
```

## Package

```bash
pip install pyinstaller
pyinstaller --noconfirm lumen_moth.spec
```

Ship the `dist/DeskCompy` folder. An `assets` folder placed next to
`DeskCompy.exe` overrides the bundled images.

## Notes

- Activity is inferred from input cadence only. No keys, titles, or screens
  are ever read.
- Custom buddies live in `%APPDATA%\DeskCompy\buddies` (or `assets/custom`).
- See `SECURITY.md` for the threat model.
