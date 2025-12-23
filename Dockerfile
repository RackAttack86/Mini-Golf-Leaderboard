FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p data

# Expose port
EXPOSE 5001

# Run with Gunicorn (production server)
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "app:app"]
