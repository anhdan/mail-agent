# utils/email_utils.py - Email Processing Utilities
import imaplib
import email
import re
import html
from email.header import decode_header
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import quopri
import base64

class EmailProcessor:
    def __init__(self):
        self.connection = None
        
    def connect_to_imap(self, account: Dict[str, Any], password: str) -> bool:
        """Connect to IMAP server"""
        try:
            print(f"Connecting to {account['imap_host']}:{account['imap_port']} for {account['email']}")
            
            # Create IMAP connection
            if account['imap_port'] == 993:
                self.connection = imaplib.IMAP4_SSL(account['imap_host'], account['imap_port'])
            else:
                self.connection = imaplib.IMAP4(account['imap_host'], account['imap_port'])
                self.connection.starttls()
            
            # Login
            self.connection.login(account['username'], password)
            
            # Select inbox
            status, messages = self.connection.select('INBOX')
            if status != 'OK':
                raise Exception(f"Failed to select INBOX: {status}")
            
            print(f"Successfully connected to {account['email']}")
            return True
            
        except Exception as e:
            print(f"IMAP connection failed for {account['email']}: {e}")
            return False
    
    def get_unread_emails(self, since_date: Optional[datetime] = None) -> List[Tuple[str, Any]]:
        """Get unread emails from IMAP server"""
        if not self.connection:
            raise Exception("Not connected to IMAP server")
        
        try:
            # Search for unread emails
            search_criteria = ['UNSEEN']
            
            # Add date filter if provided
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                search_criteria.extend(['SINCE', date_str])
            
            # Perform search
            status, messages = self.connection.search(None, *search_criteria)
            
            if status != 'OK':
                print(f"Search failed: {status}")
                return []
            
            email_ids = messages[0].split()
            print(f"Found {len(email_ids)} unread emails")
            
            emails = []
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = self.connection.fetch(email_id, '(RFC822)')
                    
                    if status == 'OK' and msg_data[0] is not None:
                        email_message = email.message_from_bytes(msg_data[0][1])
                        emails.append((email_id.decode(), email_message))
                    
                except Exception as e:
                    print(f"Error fetching email {email_id}: {e}")
                    continue
            
            return emails
            
        except Exception as e:
            print(f"Error getting unread emails: {e}")
            return []
    
    def mark_as_read(self, email_id: str):
        """Mark email as read"""
        if not self.connection:
            return
        
        try:
            self.connection.store(email_id, '+FLAGS', '\\Seen')
        except Exception as e:
            print(f"Error marking email as read: {e}")
    
    def close_connection(self):
        """Close IMAP connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            finally:
                self.connection = None
    
    def extract_email_data(self, email_message: email.message.Message) -> Dict[str, Any]:
        """Extract structured data from email message"""
        try:
            # Extract basic headers
            subject = self.decode_header_value(email_message.get('Subject', ''))
            sender = self.decode_header_value(email_message.get('From', ''))
            recipient = self.decode_header_value(email_message.get('To', ''))
            message_id = email_message.get('Message-ID', '')
            date_header = email_message.get('Date', '')
            
            # Parse date
            received_date = None
            if date_header:
                try:
                    received_date = email.utils.parsedate_to_datetime(date_header)
                except:
                    received_date = datetime.now()
            else:
                received_date = datetime.now()
            
            # Extract content
            content = self.extract_email_content(email_message)
            
            # Check for attachments
            has_attachments = self.has_attachments(email_message)
            
            # Extract priority
            priority = self.extract_priority(email_message)
            
            return {
                'message_id': message_id,
                'subject': subject or '(No Subject)',
                'sender': sender,
                'recipient': recipient,
                'received_date': received_date.isoformat(),
                'content': content,
                'content_preview': content[:500] if content else '',
                'has_attachments': has_attachments,
                'priority': priority,
                'raw_headers': dict(email_message.items())
            }
            
        except Exception as e:
            print(f"Error extracting email data: {e}")
            return {
                'message_id': email_message.get('Message-ID', ''),
                'subject': '(Error extracting subject)',
                'sender': '(Error extracting sender)',
                'recipient': '',
                'received_date': datetime.now().isoformat(),
                'content': '',
                'content_preview': '',
                'has_attachments': False,
                'priority': 'normal'
            }
    
    def decode_header_value(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ''
        
        try:
            decoded_fragments = decode_header(header_value)
            decoded_string = ''
            
            for fragment, encoding in decoded_fragments:
                if isinstance(fragment, bytes):
                    if encoding:
                        try:
                            decoded_string += fragment.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            decoded_string += fragment.decode('utf-8', errors='ignore')
                    else:
                        decoded_string += fragment.decode('utf-8', errors='ignore')
                else:
                    decoded_string += fragment
            
            return decoded_string.strip()
            
        except Exception as e:
            print(f"Error decoding header: {e}")
            return str(header_value)
    
    def extract_email_content(self, email_message: email.message.Message) -> str:
        """Extract text content from email"""
        try:
            content = ''
            
            if email_message.is_multipart():
                # Handle multipart messages
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Skip attachments
                    if 'attachment' in content_disposition:
                        continue
                    
                    if content_type == 'text/plain':
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                content = payload.decode(charset, errors='ignore')
                                break  # Use first text/plain part
                        except Exception as e:
                            print(f"Error decoding text/plain part: {e}")
                            continue
                    
                    elif content_type == 'text/html' and not content:
                        # Fallback to HTML if no plain text
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                html_content = payload.decode(charset, errors='ignore')
                                content = self.html_to_text(html_content)
                        except Exception as e:
                            print(f"Error decoding text/html part: {e}")
                            continue
            else:
                # Handle non-multipart messages
                content_type = email_message.get_content_type()
                
                if content_type == 'text/plain':
                    payload = email_message.get_payload(decode=True)
                    if payload:
                        charset = email_message.get_content_charset() or 'utf-8'
                        content = payload.decode(charset, errors='ignore')
                
                elif content_type == 'text/html':
                    payload = email_message.get_payload(decode=True)
                    if payload:
                        charset = email_message.get_content_charset() or 'utf-8'
                        html_content = payload.decode(charset, errors='ignore')
                        content = self.html_to_text(html_content)
            
            # Clean up content
            content = self.clean_email_content(content)
            return content
            
        except Exception as e:
            print(f"Error extracting email content: {e}")
            return ''
    
    def html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text"""
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # Decode HTML entities
            text = html.unescape(text)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            print(f"Error converting HTML to text: {e}")
            return html_content
    
    def clean_email_content(self, content: str) -> str:
        """Clean and normalize email content"""
        if not content:
            return ''
        
        try:
            # Remove quoted-printable encoding artifacts
            content = quopri.decodestring(content).decode('utf-8', errors='ignore')
        except:
            pass
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Remove email signatures (simple heuristic)
        lines = content.split('\n')
        clean_lines = []
        
        for i, line in enumerate(lines):
            # Stop at signature indicators
            if line.strip() in ['--', '---', 'Best regards', 'Sincerely', 'Thanks']:
                break
            
            # Stop at quoted text (replies)
            if line.strip().startswith('>') and i > 10:
                break
                
            clean_lines.append(line)
        
        content = '\n'.join(clean_lines).strip()
        
        # Limit length
        if len(content) > 5000:
            content = content[:5000] + '...'
        
        return content
    
    def has_attachments(self, email_message: email.message.Message) -> bool:
        """Check if email has attachments"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_disposition = str(part.get('Content-Disposition', ''))
                    if 'attachment' in content_disposition:
                        return True
            return False
        except:
            return False
    
    def extract_priority(self, email_message: email.message.Message) -> str:
        """Extract email priority"""
        try:
            # Check various priority headers
            priority_headers = [
                'X-Priority',
                'Priority', 
                'Importance',
                'X-MS-Mail-Priority'
            ]
            
            for header in priority_headers:
                value = email_message.get(header, '').lower()
                if value:
                    if '1' in value or 'high' in value or 'urgent' in value:
                        return 'high'
                    elif '5' in value or 'low' in value:
                        return 'low'
            
            # Check subject for priority keywords
            subject = email_message.get('Subject', '').lower()
            urgent_keywords = ['urgent', 'asap', 'important', 'critical', 'emergency']
            
            if any(keyword in subject for keyword in urgent_keywords):
                return 'high'
            
            return 'normal'
            
        except:
            return 'normal'
    
    def should_process_email(self, email_data: Dict[str, Any]) -> bool:
        """Determine if email should be processed"""
        try:
            subject = email_data.get('subject', '').lower()
            sender = email_data.get('sender', '').lower()
            content = email_data.get('content', '')
            
            # Skip if no content
            if not content or len(content.strip()) < 20:
                print(f"Skipping email with insufficient content: {subject}")
                return False
            
            # Skip automated emails
            automated_indicators = [
                'noreply', 'no-reply', 'donotreply', 'automated',
                'mailer-daemon', 'postmaster', 'system',
                'notification', 'alert'
            ]
            
            if any(indicator in sender for indicator in automated_indicators):
                print(f"Skipping automated email from: {sender}")
                return False
            
            # Skip newsletters and marketing (simple heuristic)
            newsletter_keywords = [
                'newsletter', 'unsubscribe', 'marketing',
                'promotional', 'campaign', 'offer'
            ]
            
            if any(keyword in subject for keyword in newsletter_keywords):
                print(f"Skipping newsletter/marketing email: {subject}")
                return False
            
            # Skip out of office replies
            ooo_keywords = [
                'out of office', 'auto-reply', 'automatic reply',
                'vacation', 'away message'
            ]
            
            if any(keyword in subject for keyword in ooo_keywords):
                print(f"Skipping out of office reply: {subject}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error in should_process_email: {e}")
            return True  # Default to processing if unsure

# Email provider IMAP settings
EMAIL_PROVIDERS = {
    'gmail': {
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'requires_oauth': False,  # Can use app passwords
        'notes': 'Use App Password, not regular password'
    },
    'outlook': {
        'imap_host': 'outlook.office365.com', 
        'imap_port': 993,
        'requires_oauth': False,
        'notes': 'Works with regular password or app password'
    },
    'yahoo': {
        'imap_host': 'imap.mail.yahoo.com',
        'imap_port': 993,
        'requires_oauth': False,
        'notes': 'Requires app password'
    },
    'icloud': {
        'imap_host': 'imap.mail.me.com',
        'imap_port': 993,
        'requires_oauth': False,
        'notes': 'Requires app-specific password'
    },
    'custom': {
        'imap_host': '',  # User provided
        'imap_port': 993,
        'requires_oauth': False,
        'notes': 'Custom IMAP server'
    }
}

def get_provider_settings(provider: str, custom_host: str = None, custom_port: int = None) -> Dict[str, Any]:
    """Get IMAP settings for email provider"""
    settings = EMAIL_PROVIDERS.get(provider, EMAIL_PROVIDERS['custom']).copy()
    
    if provider == 'custom' and custom_host:
        settings['imap_host'] = custom_host
        settings['imap_port'] = custom_port or 993
    
    return settings

def validate_email_account(account_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate email account data"""
    errors = []
    
    # Required fields
    required_fields = ['email', 'username', 'password', 'provider']
    for field in required_fields:
        if not account_data.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
    if account_data.get('email') and not re.match(email_pattern, account_data['email']):
        errors.append("Invalid email format")
    
    # Provider validation
    if account_data.get('provider') not in EMAIL_PROVIDERS:
        errors.append(f"Unsupported provider: {account_data.get('provider')}")
    
    # Custom provider validation
    if account_data.get('provider') == 'custom':
        if not account_data.get('imap_host'):
            errors.append("Custom provider requires imap_host")
        if not account_data.get('imap_port'):
            account_data['imap_port'] = 993  # Default
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'account_data': account_data
    }