from pydantic import BaseModel, Field


class Backup(BaseModel):
    duration: int = Field(gt=0)


class Forward(BaseModel):
    duration: int = Field(gt=0)