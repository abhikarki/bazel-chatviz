# Set environment variables. Ensure python output is sent to container's log.
# Prevent python from writing .pyc files (compiled bytecode)
ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory inside the container to /app.
WORKDIR /app


# install essential system packages needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /val/lib/apt/lists/*


COPY requirements.txt /app/requirements.txt

# install Python packages listed in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/app

EXPOSE 8001

CMD["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]