FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts contracts
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. contracts/vision.proto
COPY vault_core vault_core
COPY gateway gateway
COPY assets assets
ENV PYTHONUNBUFFERED=1
EXPOSE 8443
CMD ["uvicorn", "gateway.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8443", "--ssl-keyfile", "/certs/server-key.pem", "--ssl-certfile", "/certs/server.pem", "--ws-max-size", "300000", "--no-access-log"]
