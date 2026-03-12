from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str
    DATABASE_NAME: str
    GROQ_API_KEY: str
    LLM_MODEL: str
    CONTENT_SERVICE_URL: str
    CONFIDENCE_THRESHOLD: float = 0.35
    jwt_secret: str
    jwt_algorithm: str

    class Config:
        env_file = ".env"


settings = Settings()