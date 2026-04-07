import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
smtp_port = int(os.getenv("SMTP_PORT", "587"))
smtp_user = os.getenv("SMTP_USER")
smtp_pass = os.getenv("SMTP_PASS")

try:
    print(f"Connecting to {smtp_server}:{smtp_port} as {smtp_user}...")
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.set_debuglevel(1)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    print("SUCCESS: Login accepted!")
    server.quit()
except Exception as e:
    print(f"FAILED: {e}")
