import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import asyncio
import base64
from uuid import uuid4
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    FilePart,
    FileWithBytes,
    JSONRPCErrorResponse,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskQueryParams,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
CHECK_INTERVAL = 10

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
        'thread_messages': []
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
                        status, msg_data = mail.fetch(email_id, "(RFC822)")
                        if status == "OK":
                            raw_email = msg_data[0][1]
                            thread_msg = email.message_from_bytes(raw_email)
                            
                            thread_subject = thread_msg.get("Subject", "")
                            try:
                                decoded_subject, encoding = decode_header(thread_subject)[0]
                                if isinstance(decoded_subject, bytes):
                                    thread_subject = decoded_subject.decode(encoding or "utf-8")
                            except:
                                pass
                            
                            thread_body = ""
                            if thread_msg.is_multipart():
                                for part in thread_msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        thread_body = part.get_payload(decode=True).decode(errors="ignore")
                                        break
                            else:
                                thread_body = thread_msg.get_payload(decode=True).decode(errors="ignore")
                            
                            thread_info['thread_messages'].append({
                                'subject': thread_subject,
                                'from': thread_msg.get("From", ""),
                                'date': thread_msg.get("Date", ""),
                                'body': thread_body[:200] + "..." if len(thread_body) > 200 else thread_body
                            })
                    except:
                        continue
    except Exception as e:
        print(f"⚠️ Error getting thread info: {e}")
    
    return thread_info

async def resolve_query(prompt: str) -> str:
    """
    Send a prompt to the agent and get the response.
    
    Args:
        prompt: The question or message to send to the agent
        
    Returns:
        The agent's response as a string
    """
    agent_url = "http://localhost:8100"
    headers = {}
    
    async with httpx.AsyncClient(timeout=120, headers=headers) as httpx_client:
        try:
            card_resolver = A2ACardResolver(httpx_client, agent_url)
            card = await card_resolver.get_agent_card()
            client = A2AClient(httpx_client, agent_card=card)
            print("Connected to agent")
            message = Message(
                role='user',
                parts=[TextPart(text=prompt)],
                messageId=str(uuid4()),
                contextId=str(uuid4()),
            )
            
            payload = MessageSendParams(
                id=str(uuid4()),
                message=message,
                configuration=MessageSendConfiguration(
                    acceptedOutputModes=['text'],
                ),
            )
            
            agent_response = ""
            
            if card.capabilities.streaming:
                response_stream = client.send_message_streaming(
                    SendStreamingMessageRequest(
                        id=str(uuid4()),
                        params=payload,
                    )
                )
                
                async for result in response_stream:
                    if isinstance(result.root, JSONRPCErrorResponse):
                        return f"Error: {result.root.error.message}"
                        
                    event = result.root.result
                    
                    if isinstance(event, Message) and event.role == 'agent':
                        for part in event.parts:
                            if hasattr(part, 'text'):
                                agent_response = part.text
            else:
                event = await client.send_message(
                    SendMessageRequest(
                        id=str(uuid4()),
                        params=payload,
                    )
                )
                
                if isinstance(event.root, JSONRPCErrorResponse):
                    return f"Error: {event.root.error.message}"
                    
                result = event.root.result
                
                if isinstance(result, Message) and result.role == 'agent':
                    for part in result.parts:
                        if hasattr(part, 'text'):
                            agent_response = part.text
                            
            return agent_response
            
        except Exception as e:
            return f"Error communicating with agent: {str(e)}"

async def process_email_with_agent(mail, email_id):
    """Fetch email details and send to agent for processing"""
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
        print(f"📧 Email: {sender_email}")
        
        agent_prompt = f"""Customer Email Received:

FROM: {from_}
EMAIL ADDRESS: {sender_email}
SUBJECT: {subject}
MESSAGE ID: {message_id}
RECEIVED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

EMAIL BODY:
{body}

"""
        
        if thread_info['is_thread']:
            agent_prompt += f"""THREAD INFORMATION:
This email is part of a conversation thread with {thread_info['thread_count']} total messages.

PREVIOUS MESSAGES IN THREAD:
"""
            for idx, thread_msg in enumerate(thread_info['thread_messages'], 1):
                agent_prompt += f"""
Message {idx}:
- From: {thread_msg['from']}
- Date: {thread_msg['date']}
- Subject: {thread_msg['subject']}
- Preview: {thread_msg['body']}
"""
        
        agent_prompt += """

Please analyze this customer email, investigate the issue by coordinating with relevant agents, determine the root cause, and send an appropriate response to the customer."""
        
        print("\n🤖 Sending to Email Response Orchestrator...")
        print("="*60)
        
        response = await resolve_query(agent_prompt)
        
        print("\n📤 Agent Response:")
        print("="*60)
        print(response)
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing email: {e}")
        return False

async def monitor_emails():
    """Continuously monitor for new emails and send to agent"""
    print("🚀 Starting Email-to-Agent Monitor...")
    print(f"📧 Monitoring: {EMAIL}")
    print(f"🤖 Agent URL: http://localhost:8100")
    print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
    print("Press Ctrl+C to stop\n")
    
    mail = None
    last_email_id = None
    
    while not mail:
        mail = connect_to_gmail()
        if not mail:
            print(f"🔄 Retrying connection in {CHECK_INTERVAL} seconds...")
            await asyncio.sleep(CHECK_INTERVAL)
    
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
                    await asyncio.sleep(CHECK_INTERVAL)
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
                            await process_email_with_agent(mail, email_id)
                    except ValueError:
                        await process_email_with_agent(mail, current_latest_id)
                else:
                    print("\n✉️  First email received!")
                    await process_email_with_agent(mail, current_latest_id)
                
                last_email_id = current_latest_id
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 Email monitor stopped by user.")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print(f"🔄 Retrying in {CHECK_INTERVAL} seconds...")
            await asyncio.sleep(CHECK_INTERVAL)
    
    if mail:
        try:
            mail.logout()
        except:
            pass

async def main():
    """Main entry point"""
    try:
        await monitor_emails()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 