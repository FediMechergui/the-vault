FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY vision-py/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt Pillow==11.2.1
COPY contracts contracts
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. contracts/vision.proto
COPY vault_core vault_core
COPY vision-py/src src
COPY scripts/download_models.py scripts/download_models.py
RUN python scripts/download_models.py
ENV MODEL_DIR=/app/vision-py/models
ENV PYTHONUNBUFFERED=1
EXPOSE 50051
CMD ["python", "-m", "src.server"]
