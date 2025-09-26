from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Recruit Assest App"
    VERSION: str = "0.0.0-experimental"
    SITE_URL: str = "http://localhost:8000"

    ALLOW_ORIGINS: list[str] = ["*"]

    DB_HOST: str = "localhost"
    DB_PORT: int = 5441
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "ai_resume"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6381

    @property
    def DB_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    OPENAI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""

    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_HOST: str = ""

    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key"
    UPLOAD_FOLDER: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()