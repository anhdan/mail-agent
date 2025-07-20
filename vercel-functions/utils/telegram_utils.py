# utils/telegram_utils.py - Telegram Integration Utilities
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime

class TelegramNotifier:
    def __init__(self, config: Dict[str, Any]):
        """Initialize Telegram notifier with configuration"""
        self.bot_token = config.get('bot_token', '')
        self.chat_id = config.get('chat_id', '')
        self.username = config.get('username', '')
        self.preferences = config.get('notification_preferences', {})
        
        # Telegram API base URL
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_email_notification(self, email_data: Dict[str, Any], summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email summary notification to Telegram"""
        try:
            message = self._format_email_message(email_data, summary_data)
            
            # Send message
            response = self._send_message(
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            if response['success']:
                print(f"Telegram notification sent for: {email_data.get('subject', 'Unknown')}")
            else:
                print(f"Telegram notification failed: {response.get('error')}")
            
            return response
            
        except Exception as e:
            error_msg = f"Error sending Telegram notification: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def send_system_alert(self, alert_type: str, message: str, severity: str = 'info') -> Dict[str, Any]:
        """Send system alert to Telegram"""
        try:
            # Format system alert
            emoji_map = {
                'error': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️',
                'success': '✅'
            }
            
            emoji = emoji_map.get(severity, 'ℹ️')
            
            formatted_message = f"""{emoji} <b>System Alert</b>

<b>Type:</b> {alert_type}
<b>Severity:</b> {severity.upper()}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Message:</b>
{message}

---
Email AI Agent System"""
            
            return self._send_message(
                text=formatted_message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            error_msg = f"Error sending system alert: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def send_test_message(self, custom_message: str = None) -> Dict[str, Any]:
        """Send test message to verify Telegram configuration"""
        try:
            if custom_message:
                message = custom_message
            else:
                message = f"""🧪 <b>Test Message</b>

✅ Telegram integration is working correctly!

<b>Bot Token:</b> {'✓ Valid' if self.bot_token else '✗ Missing'}
<b>Chat ID:</b> {self.chat_id}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a test message from your Email AI Agent.

---
Email AI Agent Setup"""
            
            response = self._send_message(
                text=message,
                parse_mode='HTML'
            )
            
            if response['success']:
                print("Test message sent successfully")
            else:
                print(f"Test message failed: {response.get('error')}")
            
            return response
            
        except Exception as e:
            error_msg = f"Error sending test message: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _format_email_message(self, email_data: Dict[str, Any], summary_data: Dict[str, Any]) -> str:
        """Format email data into Telegram message"""
        # Basic email info
        subject = email_data.get('subject', '(No Subject)')
        sender = email_data.get('sender', 'Unknown')
        account = email_data.get('account_email', 'Unknown')
        received_date = email_data.get('received_date', '')
        
        # AI summary info
        summary = summary_data.get('summary', 'No summary available')
        sentiment = summary_data.get('sentiment', 'neutral')
        priority = email_data.get('priority', 'normal')
        
        # Format timestamp
        try:
            if received_date:
                dt = datetime.fromisoformat(received_date.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%Y-%m-%d %H:%M')
            else:
                formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        except:
            formatted_date = 'Unknown'
        
        # Choose emoji based on priority and sentiment
        email_emoji = self._get_email_emoji(priority, sentiment)
        
        # Build message
        message_parts = [
            f"{email_emoji} <b>New Email Summary</b>",
            "",
            f"📮 <b>Account:</b> {self._escape_html(account)}",
            f"👤 <b>From:</b> {self._escape_html(sender)}",
            f"📋 <b>Subject:</b> {self._escape_html(subject)}",
            f"⏰ <b>Received:</b> {formatted_date}"
        ]
        
        # Add priority if high
        if priority == 'high':
            message_parts.append(f"🔥 <b>Priority:</b> HIGH")
        
        # Add sentiment if not neutral
        if sentiment != 'neutral':
            sentiment_emoji = '😊' if sentiment == 'positive' else '😟'
            message_parts.append(f"{sentiment_emoji} <b>Sentiment:</b> {sentiment.title()}")
        
        # Add attachments info
        if email_data.get('has_attachments'):
            message_parts.append("📎 <b>Has Attachments</b>")
        
        # Add summary
        message_parts.extend([
            "",
            "📝 <b>Summary:</b>",
            self._escape_html(summary)
        ])
        
        # Add AI provider info if available
        if summary_data.get('provider'):
            provider_info = f"AI: {summary_data['provider']}"
            if summary_data.get('model'):
                provider_info += f" ({summary_data['model']})"
            message_parts.extend([
                "",
                f"<i>{provider_info}</i>"
            ])
        
        # Add footer
        message_parts.extend([
            "",
            "---",
            "Generated by Email AI Agent"
        ])
        
        return '\n'.join(message_parts)
    
    def _get_email_emoji(self, priority: str, sentiment: str) -> str:
        """Get appropriate emoji for email based on priority and sentiment"""
        if priority == 'high':
            return '🔥'
        elif sentiment == 'positive':
            return '😊'
        elif sentiment == 'negative':
            return '😟'
        else:
            return '📧'
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML characters for Telegram"""
        if not text:
            return ''
        
        # Escape HTML characters
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Limit length to prevent message being too long
        if len(text) > 500:
            text = text[:497] + '...'
        
        return text
    
    def _send_message(self, text: str, parse_mode: str = 'HTML', 
                     disable_web_page_preview: bool = False, 
                     reply_markup: Dict = None) -> Dict[str, Any]:
        """Send message to Telegram"""
        try:
            if not self.bot_token or not self.chat_id:
                return {
                    'success': False,
                    'error': 'Bot token or chat ID not configured'
                }
            
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview
            }
            
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)
            
            response = requests.post(url, json=payload, timeout=30)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                return {
                    'success': True,
                    'message_id': result['result']['message_id'],
                    'response': result
                }
            else:
                error_description = result.get('description', 'Unknown error')
                return {
                    'success': False,
                    'error': f"Telegram API error: {error_description}",
                    'response': result
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout - Telegram API not responding'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate Telegram configuration"""
        errors = []
        warnings = []
        
        # Check bot token format
        if not self.bot_token:
            errors.append("Bot token is missing")
        elif not self._validate_bot_token_format(self.bot_token):
            errors.append("Invalid bot token format")
        
        # Check chat ID
        if not self.chat_id:
            errors.append("Chat ID is missing")
        elif not self._validate_chat_id_format(self.chat_id):
            warnings.append("Chat ID format may be invalid")
        
        # Test bot API access
        bot_info = self._get_bot_info()
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'bot_info': bot_info,
            'chat_id': self.chat_id
        }
    
    def _validate_bot_token_format(self, token: str) -> bool:
        """Validate bot token format"""
        # Telegram bot tokens are in format: 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        import re
        pattern = r'^\d+:[A-Za-z0-9_-]+
        return bool(re.match(pattern, token))
    
    def _validate_chat_id_format(self, chat_id: str) -> bool:
        """Validate chat ID format"""
        # Chat IDs can be positive (user) or negative (group/channel)
        try:
            int(chat_id)
            return True
        except ValueError:
            return False
    
    def _get_bot_info(self) -> Dict[str, Any]:
        """Get bot information from Telegram API"""
        try:
            if not self.bot_token:
                return {'success': False, 'error': 'No bot token'}
            
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                bot_info = result['result']
                return {
                    'success': True,
                    'username': bot_info.get('username'),
                    'first_name': bot_info.get('first_name'),
                    'can_join_groups': bot_info.get('can_join_groups'),
                    'can_read_all_group_messages': bot_info.get('can_read_all_group_messages'),
                    'supports_inline_queries': bot_info.get('supports_inline_queries')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('description', 'Failed to get bot info')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error getting bot info: {str(e)}'
            }
    
    def get_chat_info(self) -> Dict[str, Any]:
        """Get information about the chat"""
        try:
            if not self.bot_token or not self.chat_id:
                return {'success': False, 'error': 'Bot token or chat ID missing'}
            
            url = f"{self.base_url}/getChat"
            payload = {'chat_id': self.chat_id}
            
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                chat_info = result['result']
                return {
                    'success': True,
                    'type': chat_info.get('type'),
                    'title': chat_info.get('title'),
                    'username': chat_info.get('username'),
                    'first_name': chat_info.get('first_name'),
                    'last_name': chat_info.get('last_name')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('description', 'Failed to get chat info')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error getting chat info: {str(e)}'
            }

def validate_telegram_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Telegram configuration data"""
    errors = []
    
    # Required fields
    if not config_data.get('bot_token'):
        errors.append("Bot token is required")
    
    if not config_data.get('chat_id'):
        errors.append("Chat ID is required")
    
    # Test the configuration if both values are provided
    if config_data.get('bot_token') and config_data.get('chat_id'):
        notifier = TelegramNotifier(config_data)
        validation_result = notifier.validate_configuration()
        
        if not validation_result['valid']:
            errors.extend(validation_result['errors'])
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'config_data': config_data
    }

def get_telegram_setup_instructions() -> str:
    """Get Telegram setup instructions"""
    return """
📱 TELEGRAM BOT SETUP INSTRUCTIONS:

1. Create a new bot:
   • Open Telegram and message @BotFather
   • Send /newbot command
   • Choose a name for your bot (e.g., "My Email Agent")
   • Choose a username (must end with 'bot', e.g., "my_email_agent_bot")
   • Copy the bot token (format: 123456789:ABC-DEF...)

2. Get your chat ID:
   Method A - Message your bot first:
   • Find your bot in Telegram and send it any message
   • Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   • Look for "chat":{"id": YOUR_CHAT_ID} in the response
   
   Method B - Use @userinfobot:
   • Message @userinfobot in Telegram
   • It will reply with your user ID (this is your chat_id)

3. For group chats:
   • Add your bot to the group
   • Send a message in the group
   • Use method A above to get the group chat ID (will be negative)

4. Test your setup:
   • Use the test function to verify your bot token and chat ID work

⚠️ IMPORTANT:
• Keep your bot token secret
• The bot can only send messages to users who have messaged it first
• For groups, the bot must be added as a member
"""