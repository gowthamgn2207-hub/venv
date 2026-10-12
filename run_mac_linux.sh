#!/bin/sh
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
. venv/bin/activate
pip install -q -r requirements.txt
echo "FinTrack is starting. Demo login: demo@fintrack.app / Demo@1234"
python app.py
