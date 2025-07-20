# api/email-processor.py - Main Email Processing Function
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime, timedelta
import traceback

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database import db
from utils.email_utils import EmailProcessor, get_provider_settings
from utils.ai_utils import AIProcessor
from utils.telegram_utils import TelegramNotifier

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests for email processing"""
        try:
            # Get request data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
            else:
                request_data = {}
            
            # Verify authorization
            if not self._verify_authorization():
                self._send_error(401, 'Unauthorized')
                return
            
            # Get trigger type
            trigger_type = request_data.get('trigger_type', 'manual')
            account_filter = request_data.get('account_id')  # Optional: process specific account
            
            print(f"Email processor started - trigger: {trigger_type}")
            db.log_system_event('email_processing_started', 
                              f"Processing triggered by: {trigger_type}")
            
            # Process emails
            result = self._process_all_emails(account_filter)
            
            # Log completion
            db.log_system_event('email_processing_completed', 
                              f"Processed {result['total_emails']} emails from {result['accounts_processed']} accounts")
            
            # Send response
            self._send_json_response({
                'success': True,
                'message': 'Email processing completed successfully',
                'trigger_type': trigger_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Email processing failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            print(traceback.format_exc())
            
            # Log error
            db.log_system_event('email_processing_error', error_msg, severity='error')
            
            self._send_error(500, error_msg)
    
    def do_GET(self):
        """Handle GET requests for status and testing"""
        try:
            if not self._verify_authorization():
                self._send_error(401, 'Unauthorized')
                return
            
            # Return system status
            status = db.get_system_health()
            
            self._send_json_response({
                'success': True,
                'status': 'Email processor is running',
                'system_health': status,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self._send_error(500, str(e))
    
    def _verify_authorization(self) -> bool:
        """Verify request authorization"""
        auth_header = self.headers.get('Authorization')
        expected_key = os.environ.get('API_SECRET_KEY')
        
        if not expected_key:
            print("WARNING: API_SECRET_KEY not set, skipping authorization")
            return True
        
        if not auth_header:
            return False
        
        return auth_header == f"Bearer {expected_key}"
    
    def _process_all_emails(self, account_filter: str = None) -> dict:
        """Process emails from all active accounts"""
        try:
            # Get active email accounts
            accounts = db.get_active_email_accounts()
            
            if account_filter:
                accounts = [acc for acc in accounts if acc['id'] == account_filter]
            
            if not accounts:
                print("No active email accounts found")
                return {
                    'accounts_processed': 0,
                    'total_emails': 0,
                    'successful_accounts': 0,
                    'failed_accounts': 0,
                    'errors': ['No active email accounts configured']
                }
            
            print(f"Processing {len(accounts)} email accounts")
            
            # Get configurations
            ai_config = db.get_ai_config()
            telegram_config = db.get_telegram_config()
            
            if not ai_config:
                print("WARNING: No AI configuration found, using fallback summaries")
            
            if not telegram_config:
                print("WARNING: No Telegram configuration found, emails will be processed but not sent")
            
            # Process each account
            total_emails = 0
            successful_accounts = 0
            failed_accounts = 0
            errors = []
            
            for account in accounts:
                try:
                    print(f"\nProcessing account: {account['email']}")
                    
                    emails_processed = self._process_account_emails(
                        account, ai_config, telegram_config
                    )
                    
                    total_emails += emails_processed
                    successful_accounts += 1
                    
                    # Update last check time
                    db.update_account_last_check(account['id'])
                    
                    print(f"Successfully processed {emails_processed} emails for {account['email']}")
                    
                except Exception as e:
                    error_msg = f"Failed to process account {account['email']}: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    errors.append(error_msg)
                    failed_accounts += 1
                    
                    # Log account-specific error
                    db.log_system_event('account_processing_error', 
                                      error_msg, 
                                      account_id=account['id'], 
                                      severity='error')
            
            return {
                'accounts_processed': len(accounts),
                'successful_accounts': successful_accounts,
                'failed_accounts': failed_accounts,
                'total_emails': total_emails,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Error in _process_all_emails: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {
                'accounts_processed': 0,
                'total_emails': 0,
                'successful_accounts': 0,
                'failed_accounts': 0,
                'errors': [error_msg]
            }
    
    def _process_account_emails(self, account: dict, ai_config: dict, telegram_config: dict) -> int:
        """Process emails for a specific account"""
        email_processor = EmailProcessor()
        emails_processed = 0
        
        try:
            # Decrypt password
            password = db.decrypt_password(account['encrypted_password'])
            
            # Connect to IMAP
            if not email_processor.connect_to_imap(account, password):
                raise Exception("Failed to connect to IMAP server")
            
            # Get unread emails since last check
            since_date = None
            if account.get('last_check_time'):
                try:
                    since_date = datetime.fromisoformat(account['last_check_time']) - timedelta(hours=1)
                except:
                    since_date = datetime.now() - timedelta(days=1)
            else:
                since_date = datetime.now() - timedelta(days=1)
            
            emails = email_processor.get_unread_emails(since_date)
            
            print(f"Found {len(emails)} unread emails")
            
            # Initialize AI processor if available
            ai_processor = None
            if ai_config:
                try:
                    ai_processor = AIProcessor(ai_config, db.decrypt_password)
                except Exception as e:
                    print(f"WARNING: Failed to initialize AI processor: {e}")
            
            # Initialize Telegram notifier if available
            telegram_notifier = None
            if telegram_config:
                try:
                    telegram_notifier = TelegramNotifier(telegram_config)
                except Exception as e:
                    print(f"WARNING: Failed to initialize Telegram notifier: {e}")
            
            # Process each email
            for email_id, email_message in emails:
                try:
                    # Extract email data
                    email_data = email_processor.extract_email_data(email_message)
                    email_data['account_id'] = account['id']
                    email_data['account_email'] = account['email']
                    
                    # Check if already processed
                    if db.is_email_processed(account['id'], email_data['message_id']):
                        print(f"Skipping already processed email: {email_data['subject']}")
                        continue
                    
                    # Check if email should be processed
                    if not email_processor.should_process_email(email_data):
                        continue
                    
                    print(f"Processing: {email_data['subject']}")
                    
                    # Generate AI summary
                    summary_data = {'summary': 'No summary available', 'sentiment': 'neutral'}
                    if ai_processor:
                        try:
                            summary_data = ai_processor.generate_email_summary(
                                email_data['content'],
                                email_data['subject'],
                                email_data['sender']
                            )
                        except Exception as e:
                            print(f"AI summarization failed: {e}")
                            summary_data = {
                                'summary': f"Email: {email_data['subject']}\nContent preview: {email_data['content'][:200]}...",
                                'sentiment': 'neutral',
                                'provider': 'fallback',
                                'error': str(e)
                            }
                    
                    # Prepare email record for database
                    email_record = {
                        'account_id': account['id'],
                        'message_id': email_data['message_id'],
                        'subject': email_data['subject'],
                        'sender': email_data['sender'],
                        'recipient': email_data['recipient'],
                        'received_date': email_data['received_date'],
                        'content_preview': email_data['content_preview'],
                        'summary': summary_data['summary'],
                        'sentiment': summary_data.get('sentiment', 'neutral'),
                        'priority': email_data['priority'],
                        'has_attachments': email_data['has_attachments'],
                        'telegram_sent': False
                    }
                    
                    # Store in database
                    stored_email = db.store_processed_email(email_record)
                    
                    # Send Telegram notification
                    if telegram_notifier:
                        try:
                            notification_result = telegram_notifier.send_email_notification(
                                email_data, summary_data
                            )
                            
                            if notification_result['success']:
                                db.mark_telegram_sent(stored_email['id'], True)
                                print("✅ Telegram notification sent")
                            else:
                                print(f"❌ Telegram notification failed: {notification_result.get('error')}")
                                
                        except Exception as e:
                            print(f"Telegram notification error: {e}")
                    
                    # Mark email as read in IMAP
                    email_processor.mark_as_read(email_id)
                    
                    emails_processed += 1
                    
                    # Log successful processing
                    db.log_system_event('email_processed', 
                                      f"Processed email: {email_data['subject'][:50]}...",
                                      account_id=account['id'],
                                      metadata={
                                          'sender': email_data['sender'],
                                          'has_summary': bool(summary_data.get('summary')),
                                          'telegram_sent': telegram_notifier is not None
                                      })
                
                except Exception as e:
                    print(f"Error processing individual email: {e}")
                    db.log_system_event('email_processing_error', 
                                      f"Failed to process email: {str(e)}",
                                      account_id=account['id'],
                                      severity='warning')
                    continue
            
            return emails_processed
            
        finally:
            # Always close IMAP connection
            email_processor.close_connection()
    
    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error(self, status_code: int, message: str):
        """Send error response"""
        self._send_json_response({
            'success': False,
            'error': message,
            'timestamp': datetime.now().isoformat()
        }, status_code)

# For local testing
if __name__ == "__main__":
    # Set up test environment
    os.environ.setdefault('API_SECRET_KEY', 'test-key')
    
    class MockRequest:
        def __init__(self):
            self.headers = {
                'Content-Length': '0',
                'Authorization': 'Bearer test-key'
            }
    
    print("Testing email processor locally...")
    
    # Create mock handler
    h = handler(MockRequest(), None, None)
    h.do_GET()
    
    print("Local test completed")