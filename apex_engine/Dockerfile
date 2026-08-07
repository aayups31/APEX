FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .
EXPOSE 7860 8000
CMD ["apexsim", "ui", "--run-dir", "artifacts/runs/reference_gru", "--config", "configs/fast.yaml"]
