from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Music Sheet Transposer"
    api_v1_prefix: str = "/api/v1"


settings = Settings()
