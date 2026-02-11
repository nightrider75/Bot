#!/usr/bin/env python3
"""Test script for email notification service.

This script tests the email notification functionality without requiring
a full API call. Useful for debugging email configuration issues.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent / "src"))

from bot.services.email_service import configure_email_service


async def test_email_service():
    """Test the email notification service with sample data."""
    print("🧪 Testing Email Notification Service")
    print("=" * 50)
    
    # Configure the email service
    try:
        email_service = configure_email_service()
        print("✅ Email service configured successfully")
    except Exception as e:
        print(f"❌ Failed to configure email service: {e}")
        return
    
    # Sample form data for testing
    sample_form_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "message": "Hello! I'm interested in your services. Could you please provide more information about your pricing and packages? I'm looking for a solution that can handle our growing business needs.\n\nThanks!\nJohn"
    }
    
    sample_submission_id = "test_submission_20260211_123456_789012"
    
    print(f"📧 Sending test email notification...")
    print(f"   Sender: notificationstoavexi@gmail.com")
    print(f"   Recipients: contact@avexi.ai, mcsr55755@gmail.com, dinesh@avexi.ai")
    print(f"   Test Data: {sample_form_data['name']} - {sample_form_data['email']}")
    
    try:
        # Send the test email
        success = await email_service.send_notification(
            sample_form_data,
            sample_submission_id
        )
        
        if success:
            print("✅ Test email sent successfully!")
            print("🎉 Email notification service is working correctly.")
            print("\nNext steps:")
            print("1. Check the recipient inboxes for the test email")
            print("2. The email service is ready for production use")
            print("3. Form submissions will now automatically send notifications")
        else:
            print("❌ Failed to send test email")
            print("📝 Check the logs above for error details")
            print("\nTroubleshooting:")
            print("1. Verify the Google App Password is correct")
            print("2. Check that 2FA is enabled on the sender account")
            print("3. Ensure the sender email has 'Less secure app access' enabled (if needed)")
            
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        print("\nTroubleshooting:")
        print("1. Check internet connection")
        print("2. Verify SMTP settings")
        print("3. Check Google App Password format")


if __name__ == "__main__":
    print("🚀 Starting Email Service Test...")
    asyncio.run(test_email_service())
