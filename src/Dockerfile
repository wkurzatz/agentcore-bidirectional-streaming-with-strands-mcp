# Use a pinned Python ARM64 base image
FROM public.ecr.aws/docker/library/python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent code
COPY agent.py .

# AgentCore Runtime expects the container to listen on port 8080
EXPOSE 8080

# Environment variables to ensure logs are sent to CloudWatch immediately
ENV PYTHONUNBUFFERED=1

# Start the agent server
CMD ["python", "agent.py"]
