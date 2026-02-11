"""Contact Form API Routes with Professional Dashboard UI.

This module provides endpoints for:
- Receiving contact form submissions from the website
- Storing submissions as JSON files locally
- Sending email notifications to configured recipients
- Displaying a professional web UI to view all submissions
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel, EmailStr, field_validator

from bot.services.email_service import configure_email_service, get_email_service

router = APIRouter()

# Storage path for contact form submissions
FORM_DATA_PATH = Path("/Users/chethan/Desktop/O/bot/form")


class ContactFormRequest(BaseModel):
    """Contact form submission request model."""

    firstName: str
    lastName: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    message: str

    @field_validator("firstName", "lastName", "message")
    @classmethod
    def validate_required_fields(cls, v: str, info) -> str:
        """Validate that required fields are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()

    @field_validator("phone", "company")
    @classmethod
    def validate_optional_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean optional fields."""
        if v:
            return v.strip()
        return v


class ContactFormResponse(BaseModel):
    """Contact form submission response model."""

    success: bool
    message: str = "Contact form submitted successfully"
    submission_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str


def ensure_form_directory():
    """Ensure the form data directory exists."""
    FORM_DATA_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"Form data directory ensured at: {FORM_DATA_PATH}")


def get_submission_filename() -> str:
    """Generate a unique filename for the submission based on timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"submission_{timestamp}.json"


def save_submission(data: ContactFormRequest) -> str:
    """Save contact form submission to a JSON file.

    Args:
        data: The contact form data to save

    Returns:
        The submission ID (filename without extension)

    Raises:
        HTTPException: If there's an error saving the file
    """
    try:
        ensure_form_directory()

        # Generate filename
        filename = get_submission_filename()
        filepath = FORM_DATA_PATH / filename

        # Add metadata
        submission_data = {
            "submission_id": filename.replace(".json", ""),
            "submitted_at": datetime.now().isoformat(),
            "data": data.model_dump(),
        }

        # Save to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(submission_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Contact form submission saved: {filename}")
        return submission_data["submission_id"]

    except Exception as e:
        logger.error(f"Error saving contact form submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save submission: {str(e)}")


def load_all_submissions() -> list[dict]:
    """Load all contact form submissions from JSON files.

    Returns:
        List of all submissions, sorted by submission time (newest first)
    """
    try:
        ensure_form_directory()

        submissions = []
        for filepath in FORM_DATA_PATH.glob("submission_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    submissions.append(data)
            except Exception as e:
                logger.error(f"Error reading submission file {filepath}: {str(e)}")
                continue

        # Sort by submission time, newest first
        submissions.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
        return submissions

    except Exception as e:
        logger.error(f"Error loading submissions: {str(e)}")
        return []


@router.post(
    "/api/contact",
    response_model=ContactFormResponse,
    responses={
        200: {"model": ContactFormResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Contact Form"],
)
async def submit_contact_form(form_data: ContactFormRequest):
    """Submit a contact form.

    This endpoint receives contact form submissions from the website, stores them
    as JSON files in the local filesystem, and sends email notifications to 
    configured recipients.

    **Required fields:**
    - firstName: User's first name
    - lastName: User's last name
    - email: User's email address (must be valid email format)
    - message: User's message or requirements

    **Optional fields:**
    - phone: User's phone number
    - company: User's company name

    **Storage location:** /Users/chethan/Desktop/O/bot/form/
    
    **Email notifications sent to:**
    - contact@avexi.ai
    - mcsr55755@gmail.com
    - dinesh@avexi.ai

    Returns:
        ContactFormResponse with success status and submission ID
    """
    try:
        # Save the submission to file
        submission_id = save_submission(form_data)
        
        # Send email notification
        email_service = get_email_service()
        if email_service is None:
            # Initialize email service if not already configured
            email_service = configure_email_service()
        
        # Send notification email (non-blocking, don't fail if email fails)
        try:
            email_sent = await email_service.send_notification(
                form_data.model_dump(), 
                submission_id
            )
            if email_sent:
                logger.info(f"Email notification sent for submission {submission_id}")
            else:
                logger.warning(f"Failed to send email notification for submission {submission_id}")
        except Exception as e:
            logger.error(f"Error sending email notification for submission {submission_id}: {str(e)}")
            # Don't fail the entire request if email fails
        
        return ContactFormResponse(
            success=True,
            message="Contact form submitted successfully. Our team will get back to you soon!",
            submission_id=submission_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in contact form submission: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/contact-submissions",
    response_class=HTMLResponse,
    tags=["Contact Form"],
    include_in_schema=False,
)
async def view_contact_submissions():
    """View all contact form submissions in a professional dashboard UI."""
    submissions = load_all_submissions()

    html_content = f"""
    <!DOCTYPE html>
    <html class="light" lang="en">
    <head>
        <meta charset="utf-8"/>
        <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
        <title>Contact Submissions Dashboard</title>
        <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
        <script id="tailwind-config">
            tailwind.config = {{
                darkMode: "class",
                theme: {{
                    extend: {{
                        colors: {{
                            "primary": "#2b8cee",
                            "background-light": "#f6f7f8",
                            "background-dark": "#101922",
                        }},
                        fontFamily: {{
                            "display": ["Inter", "sans-serif"]
                        }},
                        borderRadius: {{
                            "DEFAULT": "0.25rem",
                            "lg": "0.5rem",
                            "xl": "0.75rem",
                            "full": "9999px"
                        }},
                    }},
                }},
            }}
        </script>
        <style type="text/tailwindcss">
            .material-symbols-outlined {{
                font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
            }}
            body {{
                font-family: 'Inter', sans-serif;
            }}
            .table-sticky-header th {{
                position: sticky;
                top: 0;
                z-index: 10;
            }}
            .custom-scrollbar::-webkit-scrollbar {{
                width: 6px;
                height: 6px;
            }}
            .custom-scrollbar::-webkit-scrollbar-track {{
                background: transparent;
            }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{
                background: #e2e8f0;
                border-radius: 10px;
            }}
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {{
                background: #cbd5e1;
            }}
        </style>
    </head>
    <body class="bg-background-light dark:bg-background-dark text-[#111418] dark:text-white min-h-screen flex flex-col font-display">
        <main class="flex-1 flex flex-col min-w-0 bg-gradient-to-br from-white to-[#f0f7ff] dark:from-background-dark dark:to-slate-900">
            <header class="h-16 border-b border-[#e2e8f0] dark:border-slate-800 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-10">
                <div class="flex items-center gap-6">
                    <div class="flex items-center gap-2">
                        <div class="bg-primary size-7 rounded-lg flex items-center justify-center text-white">
                            <span class="material-symbols-outlined text-[18px]">mail</span>
                        </div>
                        <h1 class="text-sm font-bold tracking-tight">Contact Form Dashboard</h1>
                    </div>
                    <div class="h-6 w-px bg-slate-200 dark:bg-slate-700"></div>
                    <div class="flex items-center gap-3">
                        <h2 class="text-lg font-bold tracking-tight">Submissions</h2>
                        <span class="bg-primary/10 text-primary text-[11px] font-bold px-2 py-0.5 rounded-full border border-primary/20">{len(submissions)} total</span>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <button onclick="exportToCSV()" class="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                        <span class="material-symbols-outlined text-[18px]">file_download</span>
                        Export CSV
                    </button>
                    <button onclick="toggleDarkMode()" class="size-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                        <span class="material-symbols-outlined text-[18px]">dark_mode</span>
                    </button>
                </div>
            </header>

            <section class="px-8 py-6 flex flex-wrap items-center gap-4">
                <div class="flex-1 min-w-[300px]">
                    <div class="relative group">
                        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[#617589] text-[20px] group-focus-within:text-primary transition-colors">search</span>
                        <input 
                            id="searchInput"
                            class="w-full bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all placeholder:text-[#94a3b8] shadow-sm" 
                            placeholder="Search submissions, emails, or companies..." 
                            type="text"
                            onkeyup="filterSubmissions()"
                        />
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <select id="dateFilter" onchange="filterSubmissions()" class="flex items-center gap-2 px-3 py-2 bg-white dark:bg-slate-800 border border-[#e2e8f0] dark:border-slate-700 rounded-lg text-sm text-[#111418] dark:text-slate-300 hover:border-primary transition-colors shadow-sm">
                        <option value="all">All Time</option>
                        <option value="today">Today</option>
                        <option value="week">Last 7 Days</option>
                        <option value="month">Last 30 Days</option>
                    </select>
                    <button onclick="clearFilters()" class="text-sm font-semibold text-primary hover:underline px-2">
                        Clear Filters
                    </button>
                </div>
            </section>

            <section class="px-8 pb-8 flex-1 flex flex-col">
                <div class="bg-white dark:bg-slate-900 rounded-xl border border-[#e2e8f0] dark:border-slate-800 shadow-sm flex-1 flex flex-col overflow-hidden">
                    <div class="overflow-x-auto flex-1 custom-scrollbar">
                        <table class="w-full text-left border-collapse table-sticky-header min-w-[1000px]">
                            <thead>
                                <tr class="bg-slate-50 dark:bg-slate-800/50 border-b border-[#e2e8f0] dark:border-slate-800">
                                    <th class="py-4 px-4 text-[11px] font-bold uppercase tracking-wider text-[#617589]">ID</th>
                                    <th class="py-4 px-4 text-[11px] font-bold uppercase tracking-wider text-[#617589]">Date &amp; Time</th>
                                    <th class="py-4 px-4 text-[11px] font-bold uppercase tracking-wider text-[#617589]">Contact Details</th>
                                    <th class="py-4 px-4 text-[11px] font-bold uppercase tracking-wider text-[#617589]">Company</th>
                                    <th class="py-4 px-4 text-[11px] font-bold uppercase tracking-wider text-[#617589]">Phone</th>
                                    <th class="py-4 px-4 text-[11px] font-bold uppercase tracking-wider text-[#617589]">Message Preview</th>
                                    <th class="py-4 px-6 text-[11px] font-bold uppercase tracking-wider text-[#617589] text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-[#f0f2f4] dark:divide-slate-800" id="submissionsTableBody">
                                {''.join([f'''
                                <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group" 
                                    data-search="{json.dumps(sub['data']).lower()}"
                                    data-date="{sub['submitted_at']}"
                                    data-id="{sub['submission_id']}">
                                    <td class="py-4 px-4">
                                        <span class="font-mono text-xs text-[#617589]">#{sub['submission_id'][-8:]}</span>
                                    </td>
                                    <td class="py-4 px-4">
                                        <div class="flex flex-col">
                                            <span class="text-sm font-medium">{datetime.fromisoformat(sub['submitted_at']).strftime('%b %d, %Y')}</span>
                                            <span class="text-[11px] text-[#617589]">{datetime.fromisoformat(sub['submitted_at']).strftime('%I:%M %p')}</span>
                                        </div>
                                    </td>
                                    <td class="py-4 px-4">
                                        <div class="flex flex-col">
                                            <span class="text-sm font-bold">{sub['data']['firstName']} {sub['data']['lastName']}</span>
                                            <a class="text-sm text-primary hover:underline" href="mailto:{sub['data']['email']}">{sub['data']['email']}</a>
                                        </div>
                                    </td>
                                    <td class="py-4 px-4">
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
                                            {sub['data'].get('company', 'N/A')}
                                        </span>
                                    </td>
                                    <td class="py-4 px-4">
                                        <span class="text-sm text-[#617589]">{sub['data'].get('phone', 'N/A')}</span>
                                    </td>
                                    <td class="py-4 px-4">
                                        <p class="text-sm text-[#617589] max-w-[400px] truncate">{sub['data']['message'][:80]}...</p>
                                    </td>
                                    <td class="py-4 px-6 text-right">
                                        <button onclick="viewDetails('{sub['submission_id']}')" class="p-1.5 hover:bg-primary/10 hover:text-primary rounded transition-colors text-[#617589]">
                                            <span class="material-symbols-outlined text-[20px]">visibility</span>
                                        </button>
                                    </td>
                                </tr>
                                ''' for sub in submissions]) if submissions else '''
                                <tr>
                                    <td colspan="7" class="py-20 text-center">
                                        <div class="flex flex-col items-center gap-4 text-slate-400">
                                            <span class="material-symbols-outlined text-[64px]">mail_outline</span>
                                            <div>
                                                <h3 class="text-lg font-bold text-slate-600 dark:text-slate-300 mb-1">No Submissions Yet</h3>
                                                <p class="text-sm">Contact form submissions will appear here.</p>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                '''}
                            </tbody>
                        </table>
                    </div>

                    <footer class="bg-white dark:bg-slate-900 px-6 py-4 border-t border-[#e2e8f0] dark:border-slate-800 flex items-center justify-between">
                        <p class="text-xs text-[#617589] font-medium">
                            Showing <span class="text-[#111418] dark:text-white" id="visibleCount">{len(submissions)}</span> of 
                            <span class="text-[#111418] dark:text-white">{len(submissions)}</span> results
                        </p>
                        <div class="flex items-center gap-2 text-xs text-[#617589]">
                            <span>Storage: /Users/chethan/Desktop/O/bot/form/</span>
                        </div>
                    </footer>
                </div>
            </section>
        </main>

        <!-- Detail Modal -->
        <div id="detailModal" class="hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-6" onclick="closeModal(event)">
            <div class="bg-white dark:bg-slate-900 rounded-3xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto custom-scrollbar" onclick="event.stopPropagation()">
                <div id="modalContent"></div>
            </div>
        </div>

        <script>
            const submissions = {json.dumps(submissions)};

            function toggleDarkMode() {{
                document.documentElement.classList.toggle('dark');
                localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
            }}

            // Load dark mode preference
            if (localStorage.getItem('darkMode') === 'true') {{
                document.documentElement.classList.add('dark');
            }}

            function filterSubmissions() {{
                const searchTerm = document.getElementById('searchInput').value.toLowerCase();
                const dateFilter = document.getElementById('dateFilter').value;
                const rows = document.querySelectorAll('#submissionsTableBody tr[data-id]');
                let visibleCount = 0;

                const now = new Date();
                const today = now.toISOString().split('T')[0];
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

                rows.forEach(row => {{
                    const searchData = row.getAttribute('data-search');
                    const rowDate = new Date(row.getAttribute('data-date'));
                    
                    let matchesSearch = searchData.includes(searchTerm);
                    let matchesDate = true;

                    if (dateFilter === 'today') {{
                        matchesDate = rowDate.toISOString().split('T')[0] === today;
                    }} else if (dateFilter === 'week') {{
                        matchesDate = rowDate >= weekAgo;
                    }} else if (dateFilter === 'month') {{
                        matchesDate = rowDate >= monthAgo;
                    }}

                    if (matchesSearch && matchesDate) {{
                        row.style.display = '';
                        visibleCount++;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});

                document.getElementById('visibleCount').textContent = visibleCount;
            }}

            function clearFilters() {{
                document.getElementById('searchInput').value = '';
                document.getElementById('dateFilter').value = 'all';
                filterSubmissions();
            }}

            function viewDetails(submissionId) {{
                const submission = submissions.find(s => s.submission_id === submissionId);
                if (!submission) return;

                const data = submission.data;
                const submittedDate = new Date(submission.submitted_at);

                const modalHTML = `
                    <div class="p-8 md:p-10 border-b border-slate-100 dark:border-slate-800">
                        <div class="flex justify-between items-start mb-6">
                            <div class="space-y-3">
                                <div class="flex items-center gap-3 flex-wrap">
                                    <span class="bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                                        New Lead
                                    </span>
                                    <span class="text-slate-300 dark:text-slate-700">•</span>
                                    <span class="text-slate-500 dark:text-slate-400 text-sm flex items-center gap-1.5">
                                        <span class="material-symbols-outlined !text-[18px]">calendar_today</span>
                                        ${{submittedDate.toLocaleDateString('en-US', {{ month: 'long', day: 'numeric', year: 'numeric' }})}} at ${{submittedDate.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit' }})}}
                                    </span>
                                </div>
                                <h2 class="text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                                    ${{data.firstName}} ${{data.lastName}}
                                </h2>
                                ${{data.company ? `
                                <div class="flex items-center gap-2 pt-1">
                                    <span class="material-symbols-outlined !text-[20px] text-slate-400">corporate_fare</span>
                                    <span class="px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-semibold rounded-lg">${{data.company}}</span>
                                </div>
                                ` : ''}}
                            </div>
                            <button onclick="closeModal()" class="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                                <span class="material-symbols-outlined">close</span>
                            </button>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 p-8 md:p-10 bg-slate-50/50 dark:bg-slate-800/20 border-b border-slate-100 dark:border-slate-800">
                        <div class="flex flex-col gap-2.5">
                            <label class="text-xs font-bold text-slate-400 uppercase tracking-widest">Email Address</label>
                            <div class="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
                                <span class="text-base font-semibold text-slate-700 dark:text-slate-200">${{data.email}}</span>
                                <button onclick="copyToClipboard('${{data.email}}')" class="p-2 text-slate-400 hover:text-primary transition-colors hover:bg-primary/10 rounded-xl" title="Copy Email">
                                    <span class="material-symbols-outlined !text-[22px]">content_copy</span>
                                </button>
                            </div>
                        </div>
                        <div class="flex flex-col gap-2.5">
                            <label class="text-xs font-bold text-slate-400 uppercase tracking-widest">Phone Number</label>
                            <div class="flex items-center gap-3">
                                <div class="flex-1 flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
                                    <span class="text-base font-semibold text-slate-700 dark:text-slate-200">${{data.phone || 'N/A'}}</span>
                                    ${{data.phone ? `
                                    <button onclick="copyToClipboard('${{data.phone}}')" class="p-2 text-slate-400 hover:text-primary transition-colors hover:bg-primary/10 rounded-xl" title="Copy Phone">
                                        <span class="material-symbols-outlined !text-[22px]">content_copy</span>
                                    </button>
                                    ` : ''}}
                                </div>
                                ${{data.phone ? `
                                <a href="tel:${{data.phone}}" class="p-4 bg-primary text-white hover:bg-primary/90 transition-all rounded-2xl shadow-lg shadow-primary/20 active:scale-95" title="Call Now">
                                    <span class="material-symbols-outlined !text-[22px]">call</span>
                                </a>
                                ` : ''}}
                            </div>
                        </div>
                    </div>

                    <div class="p-8 md:p-10">
                        <label class="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-6">Message Body</label>
                        <div class="prose prose-slate dark:prose-invert max-w-none">
                            <div class="text-xl leading-relaxed text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 p-8 rounded-3xl italic border-l-4 border-primary/40 relative">
                                <span class="absolute -top-4 left-6 text-6xl text-primary/10 font-serif leading-none">"</span>
                                <p class="relative z-10 whitespace-pre-wrap">${{data.message}}</p>
                            </div>
                        </div>
                    </div>

                    <div class="px-8 pb-8 flex justify-between items-center text-sm text-slate-400 font-medium">
                        <p class="bg-slate-200/50 dark:bg-slate-800 px-3 py-1 rounded-md text-xs">
                            Submission ID: <span class="font-mono font-bold text-slate-600 dark:text-slate-300">${{submissionId}}</span>
                        </p>
                    </div>
                `;

                document.getElementById('modalContent').innerHTML = modalHTML;
                document.getElementById('detailModal').classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            }}

            function closeModal(event) {{
                if (!event || event.target.id === 'detailModal') {{
                    document.getElementById('detailModal').classList.add('hidden');
                    document.body.style.overflow = '';
                }}
            }}

            function copyToClipboard(text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    // Create a simple toast notification
                    const toast = document.createElement('div');
                    toast.className = 'fixed bottom-4 right-4 bg-primary text-white px-4 py-2 rounded-lg shadow-lg z-50';
                    toast.textContent = 'Copied to clipboard!';
                    document.body.appendChild(toast);
                    setTimeout(() => toast.remove(), 2000);
                }});
            }}

            function exportToCSV() {{
                const headers = ['ID', 'Date', 'First Name', 'Last Name', 'Email', 'Phone', 'Company', 'Message'];
                const rows = submissions.map(sub => [
                    sub.submission_id,
                    sub.submitted_at,
                    sub.data.firstName,
                    sub.data.lastName,
                    sub.data.email,
                    sub.data.phone || '',
                    sub.data.company || '',
                    sub.data.message
                ]);

                let csv = headers.join(',') + '\\n';
                rows.forEach(row => {{
                    csv += row.map(field => `"${{String(field).replace(/"/g, '""')}}"`).join(',') + '\\n';
                }});

                const blob = new Blob([csv], {{ type: 'text/csv' }});
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `contact-submissions-${{new Date().toISOString().split('T')[0]}}.csv`;
                a.click();
                window.URL.revokeObjectURL(url);
            }}

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {{
                if (e.key === 'Escape') {{
                    closeModal();
                }}
            }});
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
