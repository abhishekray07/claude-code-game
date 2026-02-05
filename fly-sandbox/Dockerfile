FROM ubuntu:22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install base packages including Python
RUN apt-get update && apt-get install -y \
    ttyd curl git sudo vim nano ca-certificates gnupg \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create python symlink and install common packages
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --no-cache-dir pytest requests httpx pydantic

# Install Node.js 20 from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI (via npm)
RUN npm install -g @anthropic-ai/claude-code

# Create claude user with sudo access
RUN useradd -m -s /bin/bash claude && \
    echo "claude ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Create workspace directory
RUN mkdir -p /home/claude/workspace && \
    chown -R claude:claude /home/claude

WORKDIR /home/claude/workspace

# Copy exercise files for all levels
COPY --chown=claude:claude levels/ /home/claude/levels/

# Copy entrypoint script and router
COPY --chown=claude:claude fly-sandbox/entrypoint.sh /home/claude/entrypoint.sh
COPY --chown=claude:claude fly-sandbox/router.js /home/claude/router.js
RUN chmod +x /home/claude/entrypoint.sh

USER claude

# Expose ttyd port
EXPOSE 7681

# Start with entrypoint that copies level files
CMD ["/home/claude/entrypoint.sh"]
