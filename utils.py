import os

from dotenv import load_dotenv

load_dotenv()


def getenv(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise ValueError(f"{name} is not set")
    return value


def setenv(name: str):
    os.environ[name] = getenv(name)
