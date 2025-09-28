from pydantic_settings import BaseSettings


class HttpxSettings(BaseSettings):
    MAX_CONCURRENT_REQUESTS: int = 1000
    MAX_CONNECTIONS: int = 200
    MAX_KEEPALIVE_CONNECTIONS: int = 10
    TIMEOUT: int = 30
    CLIENT_REQUEST_LIMIT: int = 50
    CLIENT_EXPIRE_SECONDS: int = 300  # 5 mins
    CLIENT_POOL_SIZE: int = 10


httpx_settings = HttpxSettings()
