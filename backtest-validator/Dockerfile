FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY btval ./btval
RUN useradd -r -u 10001 btval
USER btval
EXPOSE 8790
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8790/health')"
CMD ["uvicorn", "btval.api:app", "--host", "0.0.0.0", "--port", "8790"]
