FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Base packages + Python + Node (ttyd installed separately below)
RUN apt-get update && apt-get install -y \
    curl git vim nano ca-certificates gnupg jq \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install ttyd 1.7.7 from GitHub releases (Ubuntu's 1.6.3 has crash bugs)
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then TTYD_ARCH="x86_64" TTYD_SHA256="8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55"; \
    elif [ "$ARCH" = "aarch64" ]; then TTYD_ARCH="aarch64" TTYD_SHA256="b38acadd89d1d396a0f5649aa52c539edbad07f4bc7348b27b4f4b7219dd4165"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi && \
    curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -o /usr/bin/ttyd && \
    echo "${TTYD_SHA256}  /usr/bin/ttyd" | sha256sum -c && \
    chmod +x /usr/bin/ttyd

# Python symlink
RUN ln -s /usr/bin/python3 /usr/bin/python

# Python packages for exercises
RUN pip3 install pytest

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
