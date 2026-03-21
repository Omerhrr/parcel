"""
Email Service
ParcelFlow - Multi-tenant Logistics Platform

Provides async email sending capabilities with template support.
"""
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending emails with template support.
    
    Features:
    - Async email sending with aiosmtplib
    - Jinja2 template support for HTML emails
    - Connection pooling via SMTP
    - Development mode (prints to console instead of sending)
    - Attachment support
    - Error handling and logging
    """
    
    _instance = None
    _template_env = None
    
    def __new__(cls):
        """Singleton pattern for email service"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize email service with template environment"""
        if self._template_env is None:
            template_dir = Path(__file__).parent.parent / "templates" / "emails"
            if template_dir.exists():
                self._template_env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=select_autoescape(['html', 'xml']),
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                logger.info(f"Email templates loaded from {template_dir}")
            else:
                logger.warning(f"Email templates directory not found: {template_dir}")
                self._template_env = None
    
    @property
    def smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration"""
        return {
            'hostname': settings.SMTP_HOST,
            'port': settings.SMTP_PORT,
            'username': settings.SMTP_USER,
            'password': settings.SMTP_PASSWORD,
            'use_tls': settings.SMTP_USE_TLS,
            'start_tls': settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL,
        }
    
    @property
    def is_configured(self) -> bool:
        """Check if SMTP is configured"""
        return settings.email_configured
    
    @property
    def is_dev_mode(self) -> bool:
        """Check if running in development mode"""
        return settings.EMAIL_DEV_MODE or not self.is_configured
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render an email template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to template
            
        Returns:
            Rendered HTML string
        """
        if self._template_env is None:
            raise ValueError("Email templates not configured")
        
        template = self._template_env.get_template(template_name)
        
        # Add common context variables
        full_context = {
            **context,
            'current_year': datetime.utcnow().year,
            'app_name': settings.APP_NAME,
            'frontend_url': settings.FRONTEND_URL,
            'logo_url': f"{settings.FRONTEND_URL}/static/img/logo.png",
        }
        
        return template.render(**full_context)
    
    async def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send an email asynchronously.
        
        Args:
            to: Recipient email(s)
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text body content (optional)
            cc: CC recipients
            bcc: BCC recipients
            reply_to: Reply-to address
            attachments: List of attachments with 'filename', 'content', and 'content_type'
            headers: Additional headers
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        # Handle single recipient
        if isinstance(to, str):
            to = [to]
        
        # Development mode - print email to console
        if self.is_dev_mode:
            return self._dev_send(to, subject, html_content, text_content)
        
        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.email_from_address}>"
        message['To'] = ', '.join(to)
        
        if cc:
            message['Cc'] = ', '.join(cc)
        if bcc:
            message['Bcc'] = ', '.join(bcc)
        if reply_to:
            message['Reply-To'] = reply_to
        
        # Add custom headers
        if headers:
            for key, value in headers.items():
                message[key] = value
        
        # Add text content
        if text_content:
            message.attach(MIMEText(text_content, 'plain', 'utf-8'))
        
        # Add HTML content
        message.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                part = MIMEBase(*attachment.get('content_type', 'application/octet-stream').split('/'))
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=attachment['filename']
                )
                message.attach(part)
        
        # All recipients
        all_recipients = to + (cc or []) + (bcc or [])
        
        try:
            # Send email
            await aiosmtplib.send(
                message,
                **self.smtp_config,
                sender=settings.email_from_address,
                recipients=all_recipients
            )
            
            logger.info(f"Email sent successfully to {', '.join(to)}")
            return True
            
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending email to {to}: {str(e)}")
            return False
    
    def _dev_send(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Print email to console in development mode.
        """
        divider = "=" * 80
        print(f"\n{divider}")
        print("EMAIL (Development Mode - Not Sent)")
        print(divider)
        print(f"From: {settings.EMAIL_FROM_NAME} <{settings.email_from_address}>")
        print(f"To: {', '.join(to)}")
        print(f"Subject: {subject}")
        print(divider)
        if text_content:
            print("Text Content:")
            print(text_content)
            print(divider)
        print("HTML Content:")
        print(html_content[:1000] + "..." if len(html_content) > 1000 else html_content)
        print(divider)
        print("END OF EMAIL")
        print(divider + "\n")
        
        return True
    
    async def send_template_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        text_content: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Send an email using a Jinja2 template.
        
        Args:
            to: Recipient email(s)
            subject: Email subject
            template_name: Name of the template file
            context: Template context variables
            text_content: Plain text body content (optional)
            **kwargs: Additional arguments for send_email
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            html_content = self.render_template(template_name, context)
            return await self.send_email(
                to=to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error rendering email template {template_name}: {str(e)}")
            return False
    
    # Convenience methods for common email types
    
    async def send_password_reset(
        self,
        to: str,
        reset_url: str,
        user_name: str,
        expires_hours: int = 1
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            to: User email
            reset_url: Password reset URL with token
            user_name: User's name
            expires_hours: Hours until link expires
            
        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=to,
            subject=f"{settings.APP_NAME} - Password Reset",
            template_name="password_reset.html",
            context={
                'user_name': user_name,
                'reset_url': reset_url,
                'expires_hours': expires_hours,
            }
        )
    
    async def send_welcome(
        self,
        to: str,
        user_name: str,
        login_url: str,
        business_name: Optional[str] = None
    ) -> bool:
        """
        Send welcome email to new user.
        
        Args:
            to: User email
            user_name: User's name
            login_url: Login URL
            business_name: Business name (optional)
            
        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=to,
            subject=f"Welcome to {settings.APP_NAME}!",
            template_name="welcome.html",
            context={
                'user_name': user_name,
                'login_url': login_url,
                'business_name': business_name,
            }
        )
    
    async def send_notification(
        self,
        to: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: str = "View Details"
    ) -> bool:
        """
        Send generic notification email.
        
        Args:
            to: Recipient email
            title: Notification title
            message: Notification message
            action_url: URL for action button (optional)
            action_text: Text for action button
            
        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=to,
            subject=f"{settings.APP_NAME} - {title}",
            template_name="notification.html",
            context={
                'title': title,
                'message': message,
                'action_url': action_url,
                'action_text': action_text,
            }
        )
    
    async def send_delivery_update(
        self,
        to: str,
        waybill_number: str,
        status: str,
        status_message: str,
        tracking_url: str,
        recipient_name: Optional[str] = None
    ) -> bool:
        """
        Send delivery status update email.
        
        Args:
            to: Recipient email
            waybill_number: Waybill/tracking number
            status: Delivery status
            status_message: Status message
            tracking_url: URL to track delivery
            recipient_name: Recipient name (optional)
            
        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=to,
            subject=f"{settings.APP_NAME} - Delivery Update for {waybill_number}",
            template_name="delivery_update.html",
            context={
                'waybill_number': waybill_number,
                'status': status,
                'status_message': status_message,
                'tracking_url': tracking_url,
                'recipient_name': recipient_name,
            }
        )
    
    async def send_waybill_created(
        self,
        to: str,
        waybill_number: str,
        sender_name: str,
        receiver_name: str,
        origin: str,
        destination: str,
        tracking_url: str
    ) -> bool:
        """
        Send waybill creation notification.
        
        Args:
            to: Recipient email
            waybill_number: Waybill number
            sender_name: Sender name
            receiver_name: Receiver name
            origin: Origin location
            destination: Destination location
            tracking_url: URL to track waybill
            
        Returns:
            True if sent successfully
        """
        return await self.send_template_email(
            to=to,
            subject=f"{settings.APP_NAME} - New Shipment {waybill_number}",
            template_name="waybill_created.html",
            context={
                'waybill_number': waybill_number,
                'sender_name': sender_name,
                'receiver_name': receiver_name,
                'origin': origin,
                'destination': destination,
                'tracking_url': tracking_url,
            }
        )


# Singleton instance
email_service = EmailService()


# Convenience functions for direct import
async def send_email(*args, **kwargs) -> bool:
    """Send email using the singleton email service"""
    return await email_service.send_email(*args, **kwargs)


async def send_template_email(*args, **kwargs) -> bool:
    """Send template email using the singleton email service"""
    return await email_service.send_template_email(*args, **kwargs)


async def send_password_reset(*args, **kwargs) -> bool:
    """Send password reset email using the singleton email service"""
    return await email_service.send_password_reset(*args, **kwargs)


async def send_welcome(*args, **kwargs) -> bool:
    """Send welcome email using the singleton email service"""
    return await email_service.send_welcome(*args, **kwargs)


async def send_notification(*args, **kwargs) -> bool:
    """Send notification email using the singleton email service"""
    return await email_service.send_notification(*args, **kwargs)


async def send_delivery_update(*args, **kwargs) -> bool:
    """Send delivery update email using the singleton email service"""
    return await email_service.send_delivery_update(*args, **kwargs)


async def send_waybill_created(*args, **kwargs) -> bool:
    """Send waybill created email using the singleton email service"""
    return await email_service.send_waybill_created(*args, **kwargs)
