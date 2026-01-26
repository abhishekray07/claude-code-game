"""Spike: Test if ttyd works inside Modal sandbox."""
import modal

app = modal.App("claude-game-spike")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "build-essential", "cmake", "git", "libjson-c-dev", "libwebsockets-dev")
    .run_commands(
        # Install ttyd from source
        "git clone https://github.com/tsl0922/ttyd.git /tmp/ttyd",
        "cd /tmp/ttyd && mkdir build && cd build && cmake .. && make && make install",
        # Verify installation
        "ttyd --version",
    )
)

@app.function(image=image, timeout=300)
def test_ttyd():
    import subprocess
    import time

    # Start ttyd on port 7681
    proc = subprocess.Popen(
        ["ttyd", "-W", "-p", "7681", "bash"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)

    # Check if process is running
    if proc.poll() is None:
        print("SUCCESS: ttyd started and running")
        proc.terminate()
        return True
    else:
        stdout, stderr = proc.communicate()
        print(f"FAILED: ttyd exited with {proc.returncode}")
        print(f"stdout: {stdout.decode()}")
        print(f"stderr: {stderr.decode()}")
        return False

if __name__ == "__main__":
    with app.run():
        result = test_ttyd.remote()
        print(f"Test result: {result}")
