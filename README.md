# Spelling Bee Tutor — NeMo Guardrails (v1)

A deterministic spelling-bee quiz using NVIDIA NeMo Guardrails 0.15 (Colang v1) with Python actions grounded in a CSV word list.

## Features
- Deterministic (no external LLM calls)
- Definitions/origin/sentence on request
- Hardest → easiest, 5 words per round
- Simple CLI demo

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py

start
definition
<your spelling attempt>
origin
sentence
next
stop

Structure

app.py — Python actions, state, and a small Guardrails-compatible dummy LLM.

rails/colang/v2/flows.co — Colang v1 syntax flows (no loop; as $var).

rails/rails.yaml — minimal v1 config (no colang: block).

Notes

Built on NeMo Guardrails 0.15 (v1); designed to be fully offline and interview-friendly.

For Colang v2 (define tool, loops), use NeMo Guardrails ≥0.16 with Python 3.11 and refactor flows.


# C) Publish to GitHub (quick path)
From the project root:
```bash
git init
git add .
git commit -m "Spelling Bee Tutor: NeMo Guardrails v1 (offline deterministic demo)"
# create a repo on GitHub (via UI), then:
git branch -M main
git remote add origin https://github.com/<your-username>/spellingbee-nemo.git
git push -u origin main
