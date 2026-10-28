FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=5000 DADOS_DIR=/dados
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sistema ./sistema
COPY scripts ./scripts
COPY run.py .
RUN useradd --system --create-home app && mkdir /dados && chown app /dados
USER app
VOLUME /dados
EXPOSE 5000
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:5000/login')" || exit 1
CMD ["python", "run.py"]
