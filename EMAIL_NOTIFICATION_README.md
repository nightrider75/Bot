# Email Notification System for Contact Form

This document describes the email notification system that automatically sends emails when users submit the contact form.

## Overview

When a user submits the contact form on your website, the system will:

1. **Save the submission** to a JSON file (existing functionality)
2. **Send email notifications** to your team (NEW feature)
3. **Return success response** to the user

## Email Configuration

### Sender Email
- **Email**: `notificationstoavexi@gmail.com`
- **Password**: `foni ofak kutl bxrc` (Google App Password)
- **SMTP Server**: `smtp.gmail.com:587`

### Recipients
The following email addresses will receive notifications:
- `contact@avexi.ai`
- `mcsr55755@gmail.com`  
- `dinesh@avexi.ai`

## Email Content

Each notification email includes:

### Professional HTML Email
- **Header**: New Contact Form Submission notification
- **Contact Details**: Name, email, phone, company
- **Submission Info**: Unique submission ID and timestamp  
- **Message**: Full message from the contact
- **Quick Actions**: Reply and call buttons for immediate response

### Plain Text Fallback
- Simple text version for email clients that don't support HTML
- Contains all the same information in readable format

## Technical Implementation

### Files Modified
1. **`src/bot/services/email_service.py`** - New email service module
2. **`src/bot/routes/contact_form.py`** - Updated to include email notifications

### Key Features
- **Non-blocking**: Email failures won't prevent form submission success
- **Error Handling**: Comprehensive error logging for troubleshooting
- **Professional Templates**: HTML and text email templates
- **Security**: Uses Google App Passwords for secure authentication

## Testing

Run the test script to verify email functionality:

```bash
cd /Users/chethan/Desktop/O/bot
python test_email_service.py
```

This will send a test email to all configured recipients.

## Error Handling

The system is designed to be robust:

- **Form submission always succeeds**, even if email fails
- **Detailed logging** for debugging email issues
- **Graceful fallbacks** for various error scenarios

## Monitoring

Check application logs for:
- `Email notification sent successfully` - Successful emails
- `Failed to send email notification` - Email failures (form still saved)
- `SMTP Authentication failed` - Credential issues

## Security Notes

1. **Google App Password** is used instead of regular password
2. **2FA must be enabled** on the Google account
3. **SMTP over TLS** for encrypted email transmission
4. **Credentials are in code** - consider environment variables for production

## Troubleshooting

### Common Issues

1. **SMTP Authentication Error**
   - Verify the app password `foni ofak kutl bxrc`
   - Ensure 2FA is enabled on `notificationstoavexi@gmail.com`
   - Check that app passwords are allowed in Google account settings

2. **Connection Timeout** 
   - Check internet connectivity
   - Verify firewall isn't blocking SMTP port 587

3. **Email Not Received**
   - Check spam/junk folders
   - Verify recipient email addresses are correct
   - Check Google account sending limits

### Log Examples

**Success:**
```
INFO - Email notification sent successfully for submission submission_20260211_123456
INFO - Recipients: contact@avexi.ai, mcsr55755@gmail.com, dinesh@avexi.ai
```

**Failure:**
```
ERROR - SMTP Authentication failed: (535, b'5.7.8 Username and Password not accepted')
ERROR - Please check your email credentials and app password
```

## Next Steps

1. **Test the system** using the provided test script
2. **Monitor email delivery** for the first few form submissions
3. **Consider environment variables** for credentials in production
4. **Set up email monitoring** to track delivery success rates
