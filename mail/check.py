import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
CHECK_INTERVAL = 10
AUTO_REPLY = True

def connect_to_gmail():
    """Connect to Gmail IMAP server"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        return mail
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return None

def get_latest_email_id(mail):
    """Get the ID of the latest email"""
    try:
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        if email_ids:
            return email_ids[-1]
        return None
    except Exception as e:
        print(f"❌ Error fetching email IDs: {e}")
        return None

def get_thread_info(mail, msg):
    """Get thread information for an email"""
    thread_info = {
        'is_thread': False,
        'thread_count': 0,
        'thread_subjects': []
    }
    
    try:
        references = msg.get("References", "")
        in_reply_to = msg.get("In-Reply-To", "")
        
        if references or in_reply_to:
            thread_info['is_thread'] = True
            
            subject = msg.get("Subject", "")
            clean_subject = subject.replace("Re:", "").replace("RE:", "").replace("Fwd:", "").replace("FWD:", "").strip()
            
            status, messages = mail.search(None, f'(SUBJECT "{clean_subject}")')
            if status == "OK":
                thread_emails = messages[0].split()
                thread_info['thread_count'] = len(thread_emails)
                
                for email_id in thread_emails[-5:]:
                    try:
                        status, msg_data = mail.fetch(email_id, "(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])")
                        if status == "OK":
                            header_data = msg_data[0][1]
                            header_msg = email.message_from_bytes(header_data)
                            thread_subject = header_msg.get("Subject", "")
                            thread_from = header_msg.get("From", "")
                            thread_date = header_msg.get("Date", "")
                            
                            try:
                                decoded_subject, encoding = decode_header(thread_subject)[0]
                                if isinstance(decoded_subject, bytes):
                                    thread_subject = decoded_subject.decode(encoding or "utf-8")
                            except:
                                pass
                            
                            thread_info['thread_subjects'].append({
                                'subject': thread_subject,
                                'from': thread_from,
                                'date': thread_date
                            })
                    except:
                        continue
    except Exception as e:
        print(f"⚠️ Error getting thread info: {e}")
    
    return thread_info

def send_auto_reply(to_email, original_subject, message_id):
    """Send an automatic reply"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"Re: {original_subject}"
        msg['In-Reply-To'] = message_id
        msg['References'] = message_id
        
        body = "Noted, will reply shortly.\n\n---\nThis is an automated response."
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        print("✅ Auto-reply sent successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send auto-reply: {e}")
        return False

def process_email(mail, email_id):
    """Fetch and display email details"""
    try:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        raw_email = msg_data[0][1]
        
        msg = email.message_from_bytes(raw_email)
        
        message_id = msg.get("Message-ID", "")
        
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")
        
        from_ = msg.get("From")
        
        sender_email = ""
        if "<" in from_ and ">" in from_:
            sender_email = from_.split("<")[1].split(">")[0]
        else:
            sender_email = from_
        
        thread_info = get_thread_info(mail, msg)
        
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        
        print("\n" + "="*60)
        print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📨 Subject: {subject}")
        print(f"👤 From: {from_}")
        
        if thread_info['is_thread']:
            print(f"\n🔗 THREAD INFORMATION:")
            print(f"   📊 Total emails in thread: {thread_info['thread_count']}")
            if thread_info['thread_subjects']:
                print(f"   📧 Recent messages in thread:")
                for idx, thread_msg in enumerate(thread_info['thread_subjects'], 1):
                    print(f"      {idx}. {thread_msg['subject']}")
                    print(f"         From: {thread_msg['from']}")
                    print(f"         Date: {thread_msg['date']}")
        
        print(f"\n📄 Body:\n{body}")
        print("="*60)
        
        if AUTO_REPLY and sender_email.lower() != EMAIL.lower():
            print(f"\n📤 Sending auto-reply to: {sender_email}")
            send_auto_reply(sender_email, subject, message_id)
        
    except Exception as e:
        print(f"❌ Error processing email: {e}")

def monitor_emails():
    """Continuously monitor for new emails"""
    print("🚀 Starting email monitor...")
    print(f"📧 Monitoring: {EMAIL}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
    print(f"🤖 Auto-reply: {'Enabled' if AUTO_REPLY else 'Disabled'}")
    print("Press Ctrl+C to stop\n")
    
    mail = None
    last_email_id = None
    
    while not mail:
        mail = connect_to_gmail()
        if not mail:
            print(f"🔄 Retrying connection in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
    
    last_email_id = get_latest_email_id(mail)
    if last_email_id:
        print(f"📍 Starting from email ID: {last_email_id.decode()}")
    else:
        print("📭 No existing emails found. Waiting for new emails...")
    
    print("\n👀 Monitoring for new emails...\n")
    
    while True:
        try:
            try:
                mail.noop()
            except:
                print("🔌 Connection lost. Reconnecting...")
                mail = connect_to_gmail()
                if not mail:
                    print(f"🔄 Retrying connection in {CHECK_INTERVAL} seconds...")
                    time.sleep(CHECK_INTERVAL)
                    continue
            
            current_latest_id = get_latest_email_id(mail)
            
            if current_latest_id and current_latest_id != last_email_id:
                if last_email_id:
                    status, messages = mail.search(None, "ALL")
                    email_ids = messages[0].split()
                    
                    try:
                        last_index = email_ids.index(last_email_id)
                        new_email_ids = email_ids[last_index + 1:]
                        
                        print(f"\n✉️  {len(new_email_ids)} new email(s) received!")
                        
                        for email_id in new_email_ids:
                            process_email(mail, email_id)
                    except ValueError:
                        process_email(mail, current_latest_id)
                else:
                    print("\n✉️  First email received!")
                    process_email(mail, current_latest_id)
                
                last_email_id = current_latest_id
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 Email monitor stopped by user.")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print(f"🔄 Retrying in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
    
    if mail:
        try:
            mail.logout()
        except:
            pass

if __name__ == "__main__":
    try:
        monitor_emails()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
