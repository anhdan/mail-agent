# utils/ai_utils.py - AI Integration Utilities
import openai
import anthropic
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

class AIProcessor:
    def __init__(self, ai_config: Dict[str, Any], decrypt_function):
        """Initialize AI processor with configuration"""
        self.config = ai_config
        self.decrypt = decrypt_function
        self.provider = ai_config.get('provider', 'openai')
        
        # Decrypt API key
        encrypted_key = ai_config.get('api_key_encrypted', '')
        self.api_key = self.decrypt(encrypted_key) if encrypted_key else None
        
        # Initialize client based on provider
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize AI client based on provider"""
        try:
            if self.provider == 'openai':
                openai.api_key = self.api_key
                self.client = openai
            
            elif self.provider == 'anthropic':
                self.client = anthropic.Anthropic(api_key=self.api_key)
            
            elif self.provider == 'google':
                # Google AI implementation would go here
                # import google.generativeai as genai
                # genai.configure(api_key=self.api_key)
                pass
            
            else:
                raise ValueError(f"Unsupported AI provider: {self.provider}")
                
        except Exception as e:
            print(f"Error initializing AI client: {e}")
            self.client = None
    
    def generate_email_summary(self, content: str, subject: str, sender: str = '') -> Dict[str, Any]:
        """Generate email summary using configured AI service"""
        try:
            if not self.client:
                return self._fallback_summary(content, subject)
            
            # Prepare prompt
            prompt = self._build_prompt(content, subject, sender)
            
            # Generate summary based on provider
            if self.provider == 'openai':
                return self._generate_openai_summary(prompt)
            elif self.provider == 'anthropic':
                return self._generate_anthropic_summary(prompt)
            else:
                return self._fallback_summary(content, subject)
                
        except Exception as e:
            print(f"AI summarization error: {e}")
            return self._fallback_summary(content, subject, error=str(e))
    
    def _build_prompt(self, content: str, subject: str, sender: str = '') -> str:
        """Build AI prompt from template"""
        template = self.config.get('prompt_template', 
            'Summarize this email in 2-3 sentences, highlighting the key action items and important information:')
        
        # Add custom instructions if available
        custom_instructions = self.config.get('custom_instructions', '')
        if custom_instructions:
            template += f"\n\nAdditional instructions: {custom_instructions}"
        
        # Truncate content to fit token limits
        max_content_length = 3000  # Conservative limit
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [truncated]"
        
        # Build full prompt
        prompt_parts = [template]
        
        if sender:
            prompt_parts.append(f"\nSender: {sender}")
        
        prompt_parts.append(f"\nSubject: {subject}")
        prompt_parts.append(f"\nContent: {content}")
        
        return '\n'.join(prompt_parts)
    
    def _generate_openai_summary(self, prompt: str) -> Dict[str, Any]:
        """Generate summary using OpenAI"""
        try:
            model = self.config.get('model', 'gpt-3.5-turbo')
            max_tokens = self.config.get('max_tokens', 150)
            temperature = self.config.get('temperature', 0.3)
            
            response = self.client.ChatCompletion.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that summarizes emails concisely and accurately. Focus on key information, action items, and important details."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Extract additional insights if possible
            sentiment = self._analyze_sentiment_openai(summary)
            
            return {
                'summary': summary,
                'sentiment': sentiment,
                'provider': 'openai',
                'model': model,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None,
                'success': True
            }
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {
                'summary': f"Error generating summary: {str(e)}",
                'sentiment': 'neutral',
                'provider': 'openai',
                'success': False,
                'error': str(e)
            }
    
    def _generate_anthropic_summary(self, prompt: str) -> Dict[str, Any]:
        """Generate summary using Anthropic Claude"""
        try:
            model = self.config.get('model', 'claude-3-haiku-20240307')
            max_tokens = self.config.get('max_tokens', 150)
            
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=self.config.get('temperature', 0.3),
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            summary = message.content[0].text.strip()
            
            return {
                'summary': summary,
                'sentiment': self._analyze_sentiment_simple(summary),
                'provider': 'anthropic',
                'model': model,
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens if hasattr(message, 'usage') else None,
                'success': True
            }
            
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return {
                'summary': f"Error generating summary: {str(e)}",
                'sentiment': 'neutral',
                'provider': 'anthropic',
                'success': False,
                'error': str(e)
            }
    
    def _analyze_sentiment_openai(self, text: str) -> str:
        """Analyze sentiment using OpenAI (if enabled)"""
        try:
            if not self.config.get('enable_sentiment_analysis', False):
                return 'neutral'
            
            response = self.client.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze the sentiment of this text and respond with only one word: 'positive', 'negative', or 'neutral':\n\n{text}"
                    }
                ],
                max_tokens=10,
                temperature=0
            )
            
            sentiment = response.choices[0].message.content.strip().lower()
            
            if sentiment in ['positive', 'negative', 'neutral']:
                return sentiment
            else:
                return 'neutral'
                
        except:
            return 'neutral'
    
    def _analyze_sentiment_simple(self, text: str) -> str:
        """Simple sentiment analysis using keyword matching"""
        if not self.config.get('enable_sentiment_analysis', False):
            return 'neutral'
        
        text_lower = text.lower()
        
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'wonderful',
            'fantastic', 'perfect', 'love', 'like', 'happy',
            'pleased', 'satisfied', 'successful', 'approve'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate',
            'dislike', 'angry', 'upset', 'disappointed', 'failed',
            'error', 'problem', 'issue', 'concern', 'worried'
        ]
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        if positive_score > negative_score:
            return 'positive'
        elif negative_score > positive_score:
            return 'negative'
        else:
            return 'neutral'
    
    def _fallback_summary(self, content: str, subject: str, error: str = None) -> Dict[str, Any]:
        """Fallback summary when AI is unavailable"""
        # Create a simple extractive summary
        sentences = content.split('.')
        preview_sentences = []
        
        for sentence in sentences[:3]:  # Take first 3 sentences
            sentence = sentence.strip()
            if len(sentence) > 10:  # Only meaningful sentences
                preview_sentences.append(sentence)
        
        if preview_sentences:
            summary = '. '.join(preview_sentences) + '.'
        else:
            summary = content[:200] + '...' if len(content) > 200 else content
        
        return {
            'summary': f"Email: {subject}\n\n{summary}",
            'sentiment': 'neutral',
            'provider': 'fallback',
            'success': False,
            'error': error,
            'note': 'AI service unavailable, using fallback summary'
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate AI configuration"""
        errors = []
        warnings = []
        
        # Check API key
        if not self.api_key:
            errors.append("API key is missing or could not be decrypted")
        
        # Check provider
        if self.provider not in ['openai', 'anthropic', 'google']:
            errors.append(f"Unsupported provider: {self.provider}")
        
        # Check model
        if not self.config.get('model'):
            warnings.append("No model specified, using default")
        
        # Test API connection
        connection_test = self._test_api_connection()
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'api_connection': connection_test,
            'provider': self.provider,
            'model': self.config.get('model', 'unknown')
        }
    
    def _test_api_connection(self) -> Dict[str, Any]:
        """Test API connection with a simple request"""
        try:
            if not self.client:
                return {'success': False, 'error': 'Client not initialized'}
            
            test_prompt = "Test connection. Please respond with 'OK'."
            
            if self.provider == 'openai':
                response = self.client.ChatCompletion.create(
                    model=self.config.get('model', 'gpt-3.5-turbo'),
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=10,
                    temperature=0
                )
                return {
                    'success': True,
                    'response': response.choices[0].message.content,
                    'model': self.config.get('model')
                }
            
            elif self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.config.get('model', 'claude-3-haiku-20240307'),
                    max_tokens=10,
                    messages=[{"role": "user", "content": test_prompt}]
                )
                return {
                    'success': True,
                    'response': message.content[0].text,
                    'model': self.config.get('model')
                }
            
            else:
                return {'success': False, 'error': f'Test not implemented for {self.provider}'}
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# AI Provider configurations and defaults
AI_PROVIDERS = {
    'openai': {
        'default_model': 'gpt-3.5-turbo',
        'models': [
            'gpt-3.5-turbo',
            'gpt-3.5-turbo-16k',
            'gpt-4',
            'gpt-4-turbo-preview'
        ],
        'default_max_tokens': 150,
        'default_temperature': 0.3,
        'cost_per_1k_tokens': 0.002,  # Approximate
        'notes': 'Most cost-effective for email summaries'
    },
    'anthropic': {
        'default_model': 'claude-3-haiku-20240307',
        'models': [
            'claude-3-haiku-20240307',
            'claude-3-sonnet-20240229',
            'claude-3-opus-20240229'
        ],
        'default_max_tokens': 150,
        'default_temperature': 0.3,
        'cost_per_1k_tokens': 0.00025,  # Haiku pricing
        'notes': 'Fast and efficient for simple tasks'
    },
    'google': {
        'default_model': 'gemini-pro',
        'models': [
            'gemini-pro',
            'gemini-pro-vision'
        ],
        'default_max_tokens': 150,
        'default_temperature': 0.3,
        'cost_per_1k_tokens': 0.0005,
        'notes': 'Good alternative option'
    }
}

def get_ai_provider_info(provider: str) -> Dict[str, Any]:
    """Get information about AI provider"""
    return AI_PROVIDERS.get(provider, AI_PROVIDERS['openai'])

def validate_ai_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate AI configuration data"""
    errors = []
    
    # Required fields
    if not config_data.get('provider'):
        errors.append("Provider is required")
    
    if not config_data.get('api_key'):
        errors.append("API key is required")
    
    # Provider validation
    if config_data.get('provider') not in AI_PROVIDERS:
        errors.append(f"Unsupported provider: {config_data.get('provider')}")
    
    # Set defaults based on provider
    if config_data.get('provider') in AI_PROVIDERS:
        provider_info = AI_PROVIDERS[config_data['provider']]
        
        if not config_data.get('model'):
            config_data['model'] = provider_info['default_model']
        
        if not config_data.get('max_tokens'):
            config_data['max_tokens'] = provider_info['default_max_tokens']
        
        if not config_data.get('temperature'):
            config_data['temperature'] = provider_info['default_temperature']
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'config_data': config_data
    }