"""Generate local demo secrets once, without overwriting existing configuration."""

import secrets
from pathlib import Path


def initialize():
    root = Path(__file__).resolve().parents[1]
    destination = root / ".env"
    if destination.exists():
        print("Existing .env preserved.")
        return
    contents = (root / ".env.example").read_text()
    contents = contents.replace(
        "replace-with-a-random-secret-of-at-least-32-characters", secrets.token_urlsafe(48)
    )
    contents = contents.replace("ChangeThisDemoPassword123!", secrets.token_urlsafe(24))
    with destination.open("x") as output:
        output.write(contents)
    destination.chmod(0o600)
    print("Created .env with local demo secrets. Demo account password is DEMO_PASSWORD in that file.")


if __name__ == "__main__":
    initialize()
