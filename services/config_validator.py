"""Configuration validation at startup. Logs problems; exits only when no accounts configured."""
import logging
import os
import sys

from dotenv import load_dotenv

from services.config_loader import MARKETPLACE_OZON

load_dotenv()


def validate_configuration(accounts):
    """
    Validate .env and accounts. Log warnings for missing/invalid items.
    Exit application only if no accounts are configured.
    """
    # 1. Check .env variables for Telegram
    token = os.getenv("TELEGRAM_TOKEN")
    chat_ids = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not token or not str(token).strip():
        logging.warning("TELEGRAM_TOKEN is missing or empty; Telegram alerts and notifications will be disabled")
    if not chat_ids or not str(chat_ids).strip():
        logging.warning("TELEGRAM_CHAT_IDS is missing or empty; Telegram alerts and notifications will be disabled")

    # 2. No accounts configured → exit
    if not accounts:
        logging.error("No accounts configured. Add accounts to config/accounts.json. Exiting.")
        sys.exit(1)

    # 3. Validate each account: marketplace, name; for Ozon: client_id, api_key
    for acc in accounts:
        name = acc.get("name") or "(no name)"
        marketplace = acc.get("marketplace")
        if not marketplace:
            logging.warning("Account %s: missing marketplace; will be skipped", name)
        if not acc.get("name"):
            logging.warning("Account with marketplace %s: missing name; will be skipped", marketplace)
        if marketplace == MARKETPLACE_OZON:
            if not acc.get("client_id") or not acc.get("api_key"):
                logging.warning(
                    "Ozon account %s: missing client_id or api_key in .env; will be skipped",
                    name,
                )

    logging.info("Configuration validation completed")
