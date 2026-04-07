import os
import smtplib
import ssl
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def send_markdown_email(to_email: str, subject: str, markdown_content: str, pdf_filename: str = "TradeIQ_Report.pdf", pdf_bytes: bytes = None) -> bool:
    """
    Sends an email with the markdown report and optional PDF attachment.
    If SMTP credentials are not set in the environment, it gracefully mocks the delivery.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").replace(" ", "").strip()

    # Fallback / Mock mode if no real credentials are provided or if it's the exact placeholder
    if not smtp_user or not smtp_pass or smtp_user == "your_real_gmail_address@gmail.com":
        logger.warning(f"Dummy SMTP Credentials detected '{smtp_user}'. Simulating email dispatch to {to_email}")
        return True

    msg = EmailMessage()
    msg.set_content(f"Your requested TradeIQ market intelligence report is ready.\n\n{markdown_content}")
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email

    if pdf_bytes:
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=pdf_filename)

    try:
        # Create a secure SSL context
        context = ssl.create_default_context()
        
        # Connect to the SMTP server with a timeout to prevent hanging threads
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo() # Identify ourselves to the SMTP server
        server.starttls(context=context) # Secure the connection
        server.ehlo() # Re-identify as an encrypted connection
        server.login(smtp_user, smtp_pass) # Login with the App Password
        
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Successfully dispatched real SMTP email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"SMTP Error sending to {to_email}: {e}")
        return False
