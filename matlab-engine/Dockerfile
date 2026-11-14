FROM python:3.11-slim
WORKDIR /app
COPY matlab-engine/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY vault_core vault_core
COPY matlab-engine/service.py service.py
ENV SCORING_BACKEND=python-reference
EXPOSE 9910
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "9910", "--no-access-log"]
