import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Security & JWT Configuration
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "MY_SECRET_KEY",  # ⚠️ Change this in production!
)
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Logging Configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")  # development, production
ENABLE_JSON_LOGS = os.environ.get("ENABLE_JSON_LOGS", "false").lower() == "true"

# Email Notification Configuration
# EMAIL_BACKEND: "sendgrid" (SendGrid HTTP API) or "smtp" (e.g. Mailpit in dev)
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "sendgrid").lower()
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() == "true"
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@garimpei.com")
NOTIFICATION_FROM_NAME = os.environ.get("NOTIFICATION_FROM_NAME", "Garimpei")
NOTIFICATION_RATE_LIMIT_MINUTES = int(
    os.environ.get("NOTIFICATION_RATE_LIMIT_MINUTES", "60")
)
