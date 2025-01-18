from pydantic import BaseModel, Field

class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(max_length=1000)
    priority: int = Field(gt=0, lt=6)
    is_completed: bool

class UserRequest(BaseModel):
    username: str = Field(min_length=5)
    password: str = Field(min_length=6)

class TokenRequest(BaseModel):
    access_token: str
    token_type: str
