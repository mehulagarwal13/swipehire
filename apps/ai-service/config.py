from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://swipehire:swipehire123@localhost:5432/swipehire"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # AI
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""

    # JWT (shared with Node API)
    jwt_secret: str = "change_me_in_production_min_32_chars"
    jwt_algorithm: str = "HS256"

    # MSG91 OTP
    msg91_auth_key: str = ""
    msg91_sender_id: str = "SWIPHR"
    msg91_otp_template_id: str = ""

    # Notifications
    resend_api_key: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""

    # Search
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_master_key: str = "your_meilisearch_key"

    # Payments
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Scraping / Proxies
    proxy_host: str = "residential.oxylabs.io"
    proxy_username: str = ""
    proxy_password: str = ""
    proxy_list: str = ""           # comma-separated proxy URLs
    twocaptcha_api_key: str = ""   # 2captcha.com API key
    rapidapi_key: str = ""         # For LinkedIn Jobs API

    # Google OAuth (shared with NextAuth)
    google_client_id: str = ""
    google_client_secret: str = ""

    # App
    app_url: str = "http://localhost:8000"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384  # all-MiniLM produces 384-dim; swap to 1536 for OpenAI ada-002


settings = Settings()
