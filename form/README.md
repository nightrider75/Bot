# Contact Form API Documentation

## Overview
This API provides endpoints to submit contact form data and view submissions through a web interface.

## Storage Location
All contact form submissions are stored as JSON files in:
```
/Users/chethan/Desktop/O/bot/form/
```

Each submission is saved in a separate file with the naming pattern: `submission_YYYYMMDD_HHMMSS_microseconds.json`

---

## API Endpoints

### 1. Submit Contact Form

**Endpoint:** `POST /api/contact`

**Description:** Submit a new contact form from your website frontend.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "company": "Acme Corp",
  "message": "I want to know more about your AI solutions."
}
```

**Field Specifications:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| firstName | string | Yes | User's first name (cannot be empty) |
| lastName | string | Yes | User's last name (cannot be empty) |
| email | string | Yes | Valid email address |
| phone | string | No | User's phone number |
| company | string | No | User's company name |
| message | string | Yes | User's message (cannot be empty) |

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Contact form submitted successfully",
  "submission_id": "submission_20260112_143025_123456"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Validation error message"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Failed to save submission: error details"
}
```

---

### 2. View Submissions (Web UI)

**Endpoint:** `GET /contact-submissions`

**Description:** View all contact form submissions in a beautiful web interface.

**Access:** Open in your web browser:
```
http://localhost:8000/contact-submissions
```
(Replace `localhost:8000` with your actual server address)

**Features:**
- 📊 Real-time statistics (Total, Today, This Week)
- 🔍 Search across all fields (name, email, company, message)
- 📱 Responsive design (works on mobile and desktop)
- ⏰ Sorted by newest first
- 🎨 Beautiful, modern UI

---

## Usage Examples

### Using cURL

```bash
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "company": "Acme Corp",
    "message": "I want to know more about your AI solutions."
  }'
```

### Using JavaScript (Fetch API)

```javascript
async function submitContactForm(formData) {
  try {
    const response = await fetch('http://localhost:8000/api/contact', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        phone: formData.phone,
        company: formData.company,
        message: formData.message
      })
    });

    const result = await response.json();

    if (response.ok) {
      console.log('Success:', result);
      alert('Thank you! Your message has been submitted.');
    } else {
      console.error('Error:', result);
      alert('Error: ' + result.error);
    }
  } catch (error) {
    console.error('Network error:', error);
    alert('Failed to submit form. Please try again.');
  }
}

// Example usage with form
document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = {
    firstName: document.getElementById('firstName').value,
    lastName: document.getElementById('lastName').value,
    email: document.getElementById('email').value,
    phone: document.getElementById('phone').value,
    company: document.getElementById('company').value,
    message: document.getElementById('message').value
  };

  await submitContactForm(formData);
});
```

### Using Python (Requests)

```python
import requests

url = "http://localhost:8000/api/contact"
data = {
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "company": "Acme Corp",
    "message": "I want to know more about your AI solutions."
}

response = requests.post(url, json=data)

if response.status_code == 200:
    result = response.json()
    print(f"Success: {result}")
else:
    print(f"Error: {response.json()}")
```

---

## Frontend Integration

### HTML Form Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Us</title>
    <style>
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .required {
            color: red;
        }
        button {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <h1>Contact Us</h1>
    <form id="contactForm">
        <div class="form-group">
            <label>First Name <span class="required">*</span></label>
            <input type="text" id="firstName" required>
        </div>

        <div class="form-group">
            <label>Last Name <span class="required">*</span></label>
            <input type="text" id="lastName" required>
        </div>

        <div class="form-group">
            <label>Email <span class="required">*</span></label>
            <input type="email" id="email" required>
        </div>

        <div class="form-group">
            <label>Phone</label>
            <input type="tel" id="phone">
        </div>

        <div class="form-group">
            <label>Company</label>
            <input type="text" id="company">
        </div>

        <div class="form-group">
            <label>Message <span class="required">*</span></label>
            <textarea id="message" rows="5" required></textarea>
        </div>

        <button type="submit">Submit</button>
    </form>

    <script>
        document.getElementById('contactForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                firstName: document.getElementById('firstName').value,
                lastName: document.getElementById('lastName').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                company: document.getElementById('company').value,
                message: document.getElementById('message').value
            };

            try {
                const response = await fetch('http://localhost:8000/api/contact', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (response.ok) {
                    alert('Thank you! Your message has been submitted successfully.');
                    document.getElementById('contactForm').reset();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Failed to submit form. Please try again.');
                console.error('Error:', error);
            }
        });
    </script>
</body>
</html>
```

---

## Data Storage Format

Each submission is stored as a JSON file with the following structure:

```json
{
  "submission_id": "submission_20260112_143025_123456",
  "submitted_at": "2026-01-12T14:30:25.123456",
  "data": {
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "company": "Acme Corp",
    "message": "I want to know more about your AI solutions."
  }
}
```

---

## Testing the API

### 1. Start the server:
```bash
cd /Users/chethan/Desktop/O/bot
python -m bot.app
```

### 2. Test the API:
```bash
# Submit a test form
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "User",
    "email": "test@example.com",
    "message": "This is a test message"
  }'
```

### 3. View submissions:
Open your browser and go to:
```
http://localhost:8000/contact-submissions
```

### 4. View API documentation:
```
http://localhost:8000/docs
```

---

## CORS Configuration

The API includes CORS middleware to allow cross-origin requests from your frontend. Make sure your frontend URL is included in the CORS settings if you're hosting the frontend on a different domain.

---

## Notes for Frontend Team

1. **API Endpoint for Production:**
   - Replace `http://localhost:8000` with your production server URL
   - Example: `https://your-domain.com/api/contact`

2. **Required Fields:**
   - firstName, lastName, email, and message are mandatory
   - The API will return a 400 error if these are missing or empty

3. **Email Validation:**
   - The API validates email format automatically
   - Invalid emails will be rejected with a 400 error

4. **Success Handling:**
   - On success, you'll receive a `submission_id` that you can use for tracking
   - Show a success message to the user

5. **Error Handling:**
   - Handle both validation errors (400) and server errors (500)
   - Display user-friendly error messages

6. **Admin Access:**
   - Share this URL with admins to view submissions: `http://localhost:8000/contact-submissions`
   - Bookmark it for easy access

---

## Security Considerations

- The contact form endpoint is **public** (no authentication required)
- The submissions viewer UI is **public** by default
- Consider adding authentication to the viewer endpoint if needed
- Input validation is performed on all fields
- Email format is validated using Pydantic's EmailStr

---

## Support

If you encounter any issues or need modifications, please contact the backend team.
