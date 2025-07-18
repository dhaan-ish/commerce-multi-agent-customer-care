"""Email MCP Server - Provides email access and management tools for agents"""

import os
import imaplib
import email
from email.header import decode_header
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("email-service")

# Email Configuration
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def get_imap_connection():
    """Create and return an IMAP connection"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        return mail
    except Exception as e:
        raise Exception(f"Failed to connect to IMAP server: {e}")

def decode_email_header(header_value):
    """Decode email header value"""
    if not header_value:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            decoded_parts.append(part)
    return " ".join(decoded_parts)

def get_email_body(msg):
    """Extract the plain text body from an email message"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
    return body

def extract_email_address(from_header):
    """Extract email address from From header"""
    if "<" in from_header and ">" in from_header:
        return from_header.split("<")[1].split(">")[0]
    return from_header

# Email Sending Tools
@mcp.tool()
def send_email(to_email: str, subject: str, body: str, 
               reply_to_message_id: Optional[str] = None,
               cc: Optional[str] = None,
               bcc: Optional[str] = None) -> Dict[str, Any]:
    """
    Send an email message.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
        reply_to_message_id: Optional Message-ID to reply to (for threading)
        cc: Optional CC recipients (comma-separated)
        bcc: Optional BCC recipients (comma-separated)
    
    Returns:
        Dictionary with send status
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
            
        # Add threading headers if replying
        if reply_to_message_id:
            msg['In-Reply-To'] = reply_to_message_id
            msg['References'] = reply_to_message_id
            if not subject.startswith("Re:"):
                msg['Subject'] = f"Re: {subject}"
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            
            # Get all recipients
            recipients = [to_email]
            if cc:
                recipients.extend([e.strip() for e in cc.split(',')])
            if bcc:
                recipients.extend([e.strip() for e in bcc.split(',')])
            
            server.send_message(msg, from_addr=EMAIL, to_addrs=recipients)
        
        return {
            "success": True,
            "message": f"Email sent successfully to {to_email}",
            "subject": subject
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_email_by_id(email_id: str) -> Dict[str, Any]:
    """
    Get full details of a specific email by ID.
    
    Args:
        email_id: The email ID
    
    Returns:
        Dictionary with email details
    """
    mail = None
    try:
        mail = get_imap_connection()
        
        # Fetch the email
        status, msg_data = mail.fetch(email_id.encode(), "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Extract full email details
        email_data = {
            "id": email_id,
            "message_id": msg.get("Message-ID", ""),
            "subject": decode_email_header(msg.get("Subject", "")),
            "from": msg.get("From", ""),
            "from_email": extract_email_address(msg.get("From", "")),
            "to": msg.get("To", ""),
            "cc": msg.get("Cc", ""),
            "date": msg.get("Date", ""),
            "in_reply_to": msg.get("In-Reply-To", ""),
            "references": msg.get("References", ""),
            "body": get_email_body(msg),
            "is_reply": bool(msg.get("In-Reply-To")),
            "has_attachments": any(part.get_filename() for part in msg.walk())
        }
        
        return {
            "success": True,
            "email": email_data
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if mail:
            try:
                mail.logout()
            except:
                pass

def main():
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
