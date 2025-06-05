import os
def load_config():
    return {
        "bot_token": '7765773913:AAGYSaR0oInpRFZ0ZF4bVUGwVO6s43ORUtY',
        "DATABASE_URL": 'sqlite:///user_data.db',
        "webhook_url": os.environ.get("WEBHOOK_URL", "https://example.com")
    }
