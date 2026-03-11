from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str
    DATABASE_NAME: str
    GROQ_API_KEY: str
    LLM_MODEL: str
    CONTENT_SERVICE_URL: str
    CONFIDENCE_THRESHOLD: float = 0.35
    JWT_SECRET: str
    JWT_ALGORITHM: str

    class Config:
        env_file = ".env"


settings = Settings()