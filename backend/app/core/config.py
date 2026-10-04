from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "AgriAI"

    ENVIRONMENT: str = "development"

    DEBUG: bool = True

    DATABASE_URL: str

    SECRET_KEY: str

    # JWT Settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # <--- Add this field

    class Config:
        env_file = ".env"


settings = Settings()