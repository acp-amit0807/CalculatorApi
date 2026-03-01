import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN")


settings = Settings()