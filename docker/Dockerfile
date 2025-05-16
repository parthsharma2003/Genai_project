# Use the official Python 3.12 slim image as the base
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file from the docker/ directory to the container
COPY docker/requirements.txt /tmp/requirements.txt

# Install the dependencies listed in requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the entire application code into the container
COPY . /app

# Set the default command to run the agent.py script
CMD ["python", "adk_agent/agent.py"]