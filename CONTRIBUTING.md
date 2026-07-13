# Contributing

## Setup

```bash
python -m pip install -r requirements.txt
python scripts/build_release.py
```

## Requirements

- Keep trigger descriptions specific and preserve a mis-trigger eval.
- Add a regression case for README parsing, privacy, validation, or packaging changes.
- Keep optional details under `references/`; do not add README files inside the Skill.
- Do not include tokens, private project data, generated audit output, or local paths.
- Confirm generated examples remain source-backed and execution claims are verified.

The release build and security scan must pass before review.
