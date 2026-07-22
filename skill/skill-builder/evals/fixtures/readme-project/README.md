# Readme Demo

Readme Demo scans a directory and returns a compact JSON report for automation.

## Installation

Install the library with pip:

```bash
python -m pip install readme-demo
```

For isolated CLI use, run `pipx install readme-demo`.

## Quick Start

```pycon
>>> from readme_demo import scan

>>> report = scan("./src")
>>> print(report.to_json())
```

## CLI Usage

```bash
export DEMO_API_KEY=not-a-real-key
readme-demo scan ./src --format json
```

## Configuration

```json
{"format": "json", "recursive": true}
```
