FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先安裝依賴（利用 layer cache）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 以非 root 使用者執行
RUN useradd -m -u 1001 appuser \
    && mkdir -p /app/logs /app/data \
    && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "src"]
