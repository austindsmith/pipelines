from pydantic import  SecretStr

from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    username: str
    password: SecretStr 
