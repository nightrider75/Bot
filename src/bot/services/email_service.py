"""Email notification service for contact form submissions.

This module provides email notification functionality using Google App Passwords
for secure SMTP authentication.
"""

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, EmailStr


class EmailConfig(BaseModel):
    """Email configuration model."""
    
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str
    sender_password: str
    recipient_emails: List[EmailStr]


class ContactFormEmailService:
    """Service for sending email notifications for contact form submissions."""
    
    def __init__(self, email_config: EmailConfig):
        """Initialize the email service with configuration.
        
        Args:
            email_config: Email configuration containing SMTP settings and credentials
        """
        self.config = email_config
    
    def create_notification_email(self, form_data: dict, submission_id: str) -> MIMEMultipart:
        """Create a professional email notification for contact form submission.
        
        Args:
            form_data: The contact form submission data
            submission_id: Unique identifier for the submission
            
        Returns:
            MIMEMultipart email message ready to send
        """
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = self.config.sender_email
        msg['To'] = ', '.join(self.config.recipient_emails)
        msg['Subject'] = f"🔔 New Contact Form Submission - {form_data['name']}"
        
        # Create the HTML content
        html_content = self._create_html_email_template(form_data, submission_id)
        
        # Create the plain text content
        text_content = self._create_text_email_template(form_data, submission_id)
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        return msg
    
    def _create_html_email_template(self, form_data: dict, submission_id: str) -> str:
        """Create a professional HTML email template.
        
        Args:
            form_data: The contact form submission data
            submission_id: Unique identifier for the submission
            
        Returns:
            HTML email content
        """
        submitted_at = datetime.now()
        formatted_date = submitted_at.strftime("%B %d, %Y at %I:%M %p")
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Contact Form Submission</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .header p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }}
        .content {{
            padding: 30px;
        }}
        .contact-info {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .info-row {{
            display: flex;
            margin-bottom: 15px;
            align-items: flex-start;
        }}
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #495057;
            min-width: 100px;
            font-size: 14px;
        }}
        .info-value {{
            color: #212529;
            font-size: 14px;
            flex: 1;
        }}
        .message-section {{
            margin-top: 25px;
        }}
        .message-title {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 10px;
            font-size: 16px;
        }}
        .message-content {{
            background-color: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 0 8px 8px 0;
            font-style: italic;
            line-height: 1.7;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            border-top: 1px solid #dee2e6;
        }}
        .footer p {{
            margin: 0;
            font-size: 12px;
            color: #6c757d;
        }}
        .submission-id {{
            background-color: #e3f2fd;
            color: #1565c0;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            font-weight: 600;
        }}
        .quick-actions {{
            margin-top: 20px;
            padding: 15px;
            background-color: #e8f5e8;
            border-radius: 8px;
            text-align: center;
        }}
        .action-button {{
            display: inline-block;
            background-color: #28a745;
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 500;
            margin: 0 5px;
            font-size: 14px;
        }}
        @media (max-width: 600px) {{
            .container {{
                margin: 10px;
                border-radius: 8px;
            }}
            .content, .footer {{
                padding: 20px;
            }}
            .header {{
                padding: 20px;
            }}
            .info-row {{
                flex-direction: column;
            }}
            .info-label {{
                margin-bottom: 5px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 New Contact Form Submission</h1>
            <p>Received on {formatted_date}</p>
        </div>
        
        <div class="content">
            <div class="contact-info">
                <div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value"><strong>{form_data['name']}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Email:</span>
                    <span class="info-value"><a href="mailto:{form_data['email']}" style="color: #007bff; text-decoration: none;">{form_data['email']}</a></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Submission ID:</span>
                    <span class="info-value"><span class="submission-id">{submission_id}</span></span>
                </div>
            </div>
            
            <div class="message-section">
                <div class="message-title">📝 Message:</div>
                <div class="message-content">
                    {form_data['message'].replace(chr(10), '<br>')}
                </div>
            </div>
            
            <div class="quick-actions">
                <strong style="color: #155724;">Quick Actions:</strong><br><br>
                <a href="mailto:{form_data['email']}?subject=Re: Your Contact Form Submission&body=Hi {form_data['name']},%0D%0A%0D%0AThank you for reaching out to us." class="action-button">Reply to Contact</a>
            </div>
        </div>
        
        <div class="footer">
            <p>This notification was automatically generated from your contact form submission system.</p>
            <p>Please respond to the customer promptly to maintain excellent service standards.</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _create_text_email_template(self, form_data: dict, submission_id: str) -> str:
        """Create a plain text email template for email clients that don't support HTML.
        
        Args:
            form_data: The contact form submission data
            submission_id: Unique identifier for the submission
            
        Returns:
            Plain text email content
        """
        submitted_at = datetime.now()
        formatted_date = submitted_at.strftime("%B %d, %Y at %I:%M %p")
        
        return f"""
🔔 NEW CONTACT FORM SUBMISSION

Received on: {formatted_date}

CONTACT DETAILS:
================
Name: {form_data['name']}
Email: {form_data['email']}
Submission ID: {submission_id}

MESSAGE:
========
{form_data['message']}

QUICK ACTIONS:
=============
- Reply to: {form_data['email']}

---
This notification was automatically generated from your contact form submission system.
Please respond to the customer promptly to maintain excellent service standards.
"""
    
    async def send_notification(self, form_data: dict, submission_id: str) -> bool:
        """Send email notification for contact form submission.
        
        Args:
            form_data: The contact form submission data
            submission_id: Unique identifier for the submission
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create the email message
            msg = self.create_notification_email(form_data, submission_id)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()  # Enable encryption
                server.login(self.config.sender_email, self.config.sender_password)
                
                # Send email to all recipients
                text = msg.as_string()
                server.sendmail(
                    self.config.sender_email,
                    self.config.recipient_emails,
                    text
                )
            
            logger.info(f"Email notification sent successfully for submission {submission_id}")
            logger.info(f"Recipients: {', '.join(self.config.recipient_emails)}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {str(e)}")
            logger.error("Please check your email credentials and app password")
            return False
            
        except smtplib.SMTPConnectError as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending email notification: {str(e)}")
            return False


# Singleton instance for email service
_email_service: Optional[ContactFormEmailService] = None


def get_email_service() -> Optional[ContactFormEmailService]:
    """Get the configured email service instance.
    
    Returns:
        ContactFormEmailService instance if configured, None otherwise
    """
    return _email_service


def configure_email_service() -> ContactFormEmailService:
    """Configure and initialize the email service.
    
    Returns:
        Configured ContactFormEmailService instance
    """
    global _email_service
    
    email_config = EmailConfig(
        sender_email="notificationstoavexi@gmail.com",
        sender_password="foni ofak kutl bxrc",  # Google App Password
        recipient_emails=[
            "contact@avexi.ai",
            "mcsr55755@gmail.com", 
            "dinesh@avexi.ai"
        ]
    )
    
    _email_service = ContactFormEmailService(email_config)
    logger.info("Email service configured successfully")
    logger.info(f"Sender: {email_config.sender_email}")
    logger.info(f"Recipients: {', '.join(email_config.recipient_emails)}")
    
    return _email_service
