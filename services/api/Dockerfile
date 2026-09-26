FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY . /app
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      pip install --no-cache-dir '.[dev]'; \
    else \
      pip install --no-cache-dir .; \
    fi
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
