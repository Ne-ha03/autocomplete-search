FROM python:3.11-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY data/ data/
COPY web/ web/

ENV PORT=5000
EXPOSE 5000

WORKDIR /srv/app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]
