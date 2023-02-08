REM create python environment
python -m venv .venv

REM activate python environment
.venv\Scripts\activate

REM install requirements
.venv\Scripts\pip.exe install -r requirements.txt

REM create sample .env file
COPY ".env.json-example" "xu_rsd_gen\.env"