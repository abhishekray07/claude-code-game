FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Base packages + Python + Node
RUN apt-get update && apt-get install -y \
    ttyd curl git vim nano ca-certificates gnupg \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Python symlink
RUN ln -s /usr/bin/python3 /usr/bin/python

# Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Non-root user (no sudo needed in disposable sandbox)
RUN useradd -m -s /bin/bash claude

# Copy level files
COPY --chown=claude:claude levels/ /home/claude/levels/

# Copy entrypoint
COPY --chown=claude:claude sandbox/entrypoint.sh /home/claude/entrypoint.sh
RUN chmod +x /home/claude/entrypoint.sh

# Setup workspace
RUN mkdir -p /home/claude/workspace && \
    chown -R claude:claude /home/claude

USER claude
WORKDIR /home/claude/workspace

EXPOSE 7681

CMD ["/home/claude/entrypoint.sh"]
