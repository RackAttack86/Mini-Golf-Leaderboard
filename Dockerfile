FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/round_pictures data/profile_pictures logs .flask_session

# Expose port
EXPOSE 8080

# Run with Gunicorn (production server)
# 4 workers for 1GB RAM, increased timeout for OCR processing
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
