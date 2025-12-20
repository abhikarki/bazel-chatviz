# Base image
FROM python:3.12-slim

# Set environment variables. Ensure python output is sent to container's log.
# Prevent python from writing .pyc files (compiled bytecode)
ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1\
    PYTHONPATH=/app

# Set the working directory inside the container to /app.
WORKDIR /app


# install essential system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /val/lib/apt/lists/*


# Copying and installing requirements.txt earlier than main code so pip install
# command only re-runs when requirements.txt actually changes, saving significant build time on subsequent code changes
COPY requirements.txt .

# install Python packages listed in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]