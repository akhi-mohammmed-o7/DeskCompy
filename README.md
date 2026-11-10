# DeskCompy

A tiny desk companion that watches your rhythm (never your words) and keeps
you company while you work, study, or play.

Choose from eight hand-drawn buddies: moth, cat, frog, ghost, axolotl, dog,
bunny, and owl. Their expressions and small idle actions follow the activity
rhythm. Ambient chatter starts off, so the companion stays out of the way.

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
- The chat panel uses short, scripted local replies. Its transcript clears
  when the panel closes; no chat is saved or sent anywhere.
- Speech popups are brief and click-through. Turn ambient small talk on in
  Customize if you want the buddy to chime in on its own.
- Custom buddies live in `%APPDATA%\DeskCompy\buddies` (or `assets/custom`).
- See `SECURITY.md` for the threat model.
