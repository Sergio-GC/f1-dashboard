import os
import requests
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


_CET = ZoneInfo("Europe/Paris")

_TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def start_scheduler():
    """Start the background notification checker."""
    def _loop():
        while True:
            try:
                _check_notification_need()
            except Exception as e:
                print(f"Scheduler error: {e}")
            time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print("Telegram notification scheduler started")


def _check_notification_need():
    """Check if a notification needs to be sent. This method is called every minute"""
    from services.f1_service import get_current_races

    now = datetime.now(_CET)

    try:
        next_race, _ = get_current_races()
    except Exception as e:
        print(f"There was an error fetching the next race: {e}")
        return
    
    if not next_race: return

    # Parse race data
    race_date_str = next_race["date"]
    race_date = datetime.strptime(race_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).astimezone(_CET).date()
    days_until_race = (race_date - now.date()).days


    # ── Monday 08:00 — Race week preview ──
    if now.weekday() == 0 and now.hour == 8 and now.minute == 0:
        if 0 <= days_until_race <= 6:
            msg = _build_race_preview(next_race, "🗓️ RACE WEEK")
            send_message(msg)

    # ── Friday 19:00 — Weekend reminder ──
    if now.weekday() == 4 and now.hour == 19 and now.minute == 0:
        if 0 <= days_until_race <= 2:
            msg = _build_race_preview(next_race, "📣 THIS WEEKEND")
            send_message(msg)


    # ── 1 hour before qualifying and race ──
    sessions = next_race.get("sessions", {})
    for key in ["qualifying", "race"]:
        if key not in sessions:
            continue

        session_utc = sessions[key]["utc"]
        try:
            session_dt = datetime.strptime(session_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        diff = session_dt - now.astimezone(timezone.utc)
        minutes_until = diff.total_seconds() / 60

        if 59 <= minutes_until < 60:
            label = "Qualifying" if key == "qualifying" else "Race"
            session_cet = session_dt.astimezone(_CET)
            send_message(
                f"⏰ <b>{label} in 1 hour!</b>\n\n"
                f"🏁 {next_race['name']}\n"
                f"🕐 {session_cet.strftime('%H:%M')} CET"
            )


def _build_race_preview(race, heading):
    """Build a Telegram message with race info and session times."""
    lines = [
        f"<b>{heading}</b>",
        "",
        f"🏁 <b>{race['name']}</b>",
        f"📍 {race['circuit_name']}, {race['locality']}, {race['country']}",
        "",
    ]

    sessions = race.get("sessions", {})
    # Show sessions in a logical order
    for key, label in [
        ("sprint_qualifying", "Sprint Quali"),
        ("sprint", "Sprint"),
        ("qualifying", "Qualifying"),
        ("race", "Race"),
    ]:
        if key in sessions:
            lines.append(f"  {label}: <b>{sessions[key]['display']}</b>")

    return "\n".join(lines)


def send_message(text):
    """Send a message via telegram"""
    if not _TELEGRAM_BOT_TOKEN or not _TELEGRAM_CHAT_ID:
        print("Telegram has not been configured in the .env file. Skipping the text")
        return
    
    try:
        url = f"https://api.telegram.org/bot{_TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            json = {
                "chat_id": _TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10
        )

        if not response.ok:
            print(f"Telegram error: {response.status_code} {response.text}")
        else:
            print("Message sent successfully")

    except Exception as e:
        print(f"Telegram messaging error: {e}")