FROM ubuntu:22.04

# Install ttyd
RUN apt-get update && apt-get install -y \
    ttyd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -s /bin/bash testuser

# Expose ttyd port
EXPOSE 7681

# Run ttyd as testuser's shell
CMD ["ttyd", "-W", "-p", "7681", "su", "-", "testuser"]
