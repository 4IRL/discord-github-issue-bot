FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY issue_bot/ issue_bot/

RUN useradd --create-home --uid 10001 bot
USER bot

# Python runs as PID 1 and ignores SIGTERM; SIGINT triggers discord.py's graceful shutdown.
STOPSIGNAL SIGINT

CMD ["python", "-m", "issue_bot"]
