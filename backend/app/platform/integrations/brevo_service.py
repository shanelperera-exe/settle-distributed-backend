import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from jinja2 import Environment, FileSystemLoader

from app.platform.core.config import settings

logger = logging.getLogger(__name__)

class BrevoEmailService:
    """
    Service for sending emails via Brevo (formerly Sendinblue) API.
    """
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.sender_email = settings.BREVO_SENDER_EMAIL
        self.sender_name = settings.BREVO_SENDER_NAME
        self.api_url = "https://api.brevo.com/v3/smtp/email"
        
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "emails")
        self.env = Environment(loader=FileSystemLoader(template_dir))

    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        to_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[Dict[str, str]]] = None,
        bcc: Optional[List[Dict[str, str]]] = None,
    ) -> bool:
        """
        Sends an email using the Brevo API.
        
        Args:
            to_email: The recipient's email address.
            subject: The email subject.
            html_content: The HTML body of the email.
            to_name: (Optional) The recipient's name.
            sender_email: (Optional) Override default sender email.
            sender_name: (Optional) Override default sender name.
            reply_to: (Optional) Reply-to email address.
            cc: (Optional) List of CC recipients [{"email": "x@x.com", "name": "X"}].
            bcc: (Optional) List of BCC recipients [{"email": "x@x.com", "name": "X"}].
            
        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        if not self.api_key:
            logger.warning("Brevo API key is missing. Email not sent.")
            return False

        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }

        sender = {
            "name": sender_name or self.sender_name,
            "email": sender_email or self.sender_email,
        }

        recipient = {"email": to_email}
        if to_name:
            recipient["name"] = to_name

        payload: Dict[str, Any] = {
            "sender": sender,
            "to": [recipient],
            "subject": subject,
            "htmlContent": html_content,
        }

        if reply_to:
            payload["replyTo"] = {"email": reply_to}
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                if response.status_code in (201, 202):
                    logger.info(f"Email successfully sent to {to_email}")
                    return True
                else:
                    logger.error(f"Failed to send email. Brevo API response [{response.status_code}]: {response.text}")
                    return False
        except httpx.RequestError as e:
            logger.error(f"Error communicating with Brevo API: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while sending email via Brevo: {e}")
            return False

    async def send_template_email(
        self,
        template_name: str,
        context: Dict[str, Any],
        to_email: str,
        subject: str,
        **kwargs
    ) -> bool:
        """
        Renders an HTML template with Jinja2 and sends it.
        
        Args:
            template_name: Name of the template file (e.g. 'welcome.html')
            context: Dictionary of variables to inject into the template
            to_email: The recipient's email address
            subject: The email subject
            **kwargs: Any additional arguments passed to send_email (like to_name, cc, bcc, etc.)
        """
        # Ensure year is always available for the footer
        if "year" not in context:
            context["year"] = datetime.now().year
            
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render email template '{template_name}': {e}")
            return False
            
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            **kwargs
        )

# Export an instance for easier usage
email_service = BrevoEmailService()
