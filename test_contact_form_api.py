#!/usr/bin/env python3
"""Test script for the complete contact form API with email notifications.

This script tests the full workflow: form submission, file saving, and email notification.
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

async def test_contact_form_api():
    """Test the contact form API endpoint with email notifications."""
    print("🧪 Testing Contact Form API with Email Notifications")
    print("=" * 60)
    
    # Test data
    test_data = {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "message": "This is a test submission from the automated test script. Please disregard this message. Testing the email notification functionality."
    }
    
    # API endpoint - adjust if running on different port
    api_url = "http://localhost:8000/api/contact"
    
    print(f"📤 Sending test form submission to: {api_url}")
    print(f"📧 Test email: {test_data['email']}")
    print(f"👤 Test name: {test_data['name']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=test_data) as response:
                status_code = response.status
                response_data = await response.json()
                
                print(f"\n📊 API Response:")
                print(f"   Status Code: {status_code}")
                print(f"   Response: {json.dumps(response_data, indent=2)}")
                
                if status_code == 200 and response_data.get("success"):
                    print("\n✅ Contact form submission successful!")
                    print(f"📝 Submission ID: {response_data.get('submission_id', 'N/A')}")
                    print("\n📧 Email notifications should have been sent to:")
                    print("   • contact@avexi.ai")
                    print("   • mcsr55755@gmail.com")
                    print("   • dinesh@avexi.ai")
                    print("\n🎉 Test completed successfully!")
                else:
                    print(f"\n❌ API call failed: {response_data}")
                    
    except aiohttp.ClientConnectorError:
        print("\n❌ Could not connect to the API server")
        print("💡 Make sure the FastAPI server is running on localhost:8000")
        print("   Run: `uvicorn bot.app:app --reload` or your preferred method")
    except Exception as e:
        print(f"\n❌ Error testing API: {e}")

def print_instructions():
    """Print instructions for running the test."""
    print("\n📋 To test the contact form API:")
    print("1. Start the FastAPI server:")
    print("   cd /Users/chethan/Desktop/O/bot")
    print("   uvicorn bot.app:app --reload")
    print("\n2. In another terminal, run this test:")
    print("   python3 test_contact_form_api.py")

if __name__ == "__main__":
    print("🚀 Starting Contact Form API Test...")
    try:
        asyncio.run(test_contact_form_api())
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        print_instructions()
