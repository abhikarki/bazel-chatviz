from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_region: str = "us-east-1"
    s3_bucket: str = "bazel-chatviz-bucket"
    openai_api_key: str = os.getenv("OPENAI_API_KEY")

    # celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    # celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str ="redis://localhost:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()