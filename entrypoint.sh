#!/bin/sh
set -e

# --- Validate required env vars ---
fail=0
for var in AMAZON_SCRAPER_DISCORD_TOKEN; do
  eval val=\$$var
  if [ -z "$val" ]; then
    echo "ERROR: $var is required but not set" >&2
    fail=1
  fi
done
[ "$fail" -eq 1 ] && exit 1

if [ ! -f /app/data/cookies.txt ]; then
  echo "WARNING: /app/data/cookies.txt not found — coupon fetching will fail" >&2
fi

# --- Generate Variables.py from environment ---
cat > /app/Variables.py << 'PYEOF'
import os

class Constants:
    HOST = os.environ.get("AMAZON_SCRAPER_MONGO_HOST", "192.168.68.102")
    PORT = os.environ.get("AMAZON_SCRAPER_MONGO_PORT", "27017")
    TESSERACT_LOCATION = os.environ.get("AMAZON_SCRAPER_TESSERACT", "/usr/bin/tesseract")
    PROXY = os.environ.get("AMAZON_SCRAPER_PROXY", "")
    LOG_CHANNEL = int(os.environ["AMAZON_SCRAPER_LOG_CHANNEL"]) if os.environ.get("AMAZON_SCRAPER_LOG_CHANNEL") else None
    ERROR_CHANNEL = int(os.environ["AMAZON_SCRAPER_ERROR_CHANNEL"]) if os.environ.get("AMAZON_SCRAPER_ERROR_CHANNEL") else None
    ANNOUNCEMENT_CHANNEL = int(os.environ["AMAZON_SCRAPER_ANNOUNCEMENT_CHANNEL"]) if os.environ.get("AMAZON_SCRAPER_ANNOUNCEMENT_CHANNEL") else None
    FEEDBACK_CHANNEL = int(os.environ["AMAZON_SCRAPER_FEEDBACK_CHANNEL"]) if os.environ.get("AMAZON_SCRAPER_FEEDBACK_CHANNEL") else None
    SUPPORT_USERS = [int(x) for x in os.environ.get("AMAZON_SCRAPER_SUPPORT_USERS", "").split(",") if x.strip()]
    SUPPORT_GUILD = [int(x) for x in os.environ.get("AMAZON_SCRAPER_SUPPORT_GUILD", "").split(",") if x.strip()]
    TIP = "Tip: **Avoid** fetching coupon code unless you are **fully interested in the product.**"
    AUTHOR_NAME = os.environ.get("AMAZON_SCRAPER_AUTHOR_NAME", "Arshan")
    MAINTENANCE = os.environ.get("AMAZON_SCRAPER_MAINTENANCE", "false").lower() == "true"
    OVERRIDE_BLACKLIST = os.environ.get("AMAZON_SCRAPER_OVERRIDE_BLACKLIST", "false").lower() == "true"
    TOKEN = os.environ["AMAZON_SCRAPER_DISCORD_TOKEN"]
PYEOF

exec "$@"
