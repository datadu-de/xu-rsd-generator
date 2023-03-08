REM create python environment
python -m venv .venv

REM install requirements
.\.venv\Scripts\pip.exe install -r requirements.txt

REM create sample .env file
COPY ".env.example" "xu_rsd_gen\.env"
