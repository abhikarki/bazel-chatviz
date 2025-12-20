# Base Image
FROM python:3.12-slim AS base

# Set environment variables. Ensure python output is sent to container's log.
# Prevent python from writing .pyc files (compiled bytecode)
ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1\
    PYTHONPATH=/app

# Set the working directory inside the container to /app.
WORKDIR /app

# install essential system packages needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Creating a non-root user
RUN addgroup --system celery && adduser --system --ingroup celery celery

# the following copy and install are still as root for system wide access
COPY requirements.txt /app/requirements.txt

# install Python packages listed in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Now we will copy code with ownership change
# using --chown to make 'celery' user the owner of the app files
# copy the application code.
COPY --chown=celery:celery src /app/src

# switching the user, now we are no longer root
USER celery

# command to start the Celery worker.
CMD ["celery", "-A", "src.tasks.tasks:app", "worker", "--loglevel=info"]