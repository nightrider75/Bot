"""
CSV Manager Routes - Universal CSV UI for bot user data.

This provides a beautiful web UI for uploading/downloading CSV files
that works with ANY user data provider (PostgreSQL, LocalCSV, InMemory).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from bot.config import settings
from bot.services.csv_manager_service import CSVManagerService

logger = logging.getLogger(__name__)

router = APIRouter()


class UploadResponse(BaseModel):
    """Response model for CSV upload."""

    success: bool
    users_added: int
    users_updated: int
    total_processed: int
    errors: list[str]
    error_count: int


class StatsResponse(BaseModel):
    """Response model for user data statistics."""

    total_users: int
    total_fields: int
    field_names: list[str]
    provider: str


@router.get("/", response_class=HTMLResponse)
async def csv_manager_ui():
    """
    Render the CSV Manager UI.

    This beautiful UI automatically works with whatever provider is configured
    (PostgreSQL, LocalCSV, or InMemory) via HUB_CONFIG__USERDATA_PROVIDER.
    """
    provider_name = settings.hub_config.userdata_provider.value

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CSV Data Manager</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #f5f5f5;
                min-height: 100vh;
                padding: 40px 20px;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                padding: 40px;
            }}
            
            h1 {{
                font-size: 32px;
                color: #1a1a1a;
                margin-bottom: 30px;
                font-weight: 400;
            }}
            
            .status-section {{
                margin-bottom: 40px;
            }}
            
            .status-section h2 {{
                font-size: 18px;
                color: #1a1a1a;
                margin-bottom: 12px;
                font-weight: 600;
            }}
            
            .status-info {{
                color: #22c55e;
                font-size: 14px;
                margin-bottom: 4px;
            }}
            
            .status-meta {{
                color: #666;
                font-size: 13px;
            }}
            
            .upload-section {{
                border: 2px dashed #d1d5db;
                border-radius: 8px;
                padding: 60px 40px;
                text-align: center;
                margin-bottom: 40px;
                transition: all 0.2s;
            }}
            
            .upload-section:hover {{
                border-color: #3b82f6;
                background: #fafafa;
            }}
            
            .upload-section.drag-over {{
                border-color: #3b82f6;
                background: #eff6ff;
            }}
            
            .upload-section h3 {{
                font-size: 20px;
                color: #1a1a1a;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .upload-section p {{
                color: #666;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            
            .file-upload-area {{
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 12px;
            }}
            
            .file-input {{
                display: none !important;
                position: absolute;
                opacity: 0;
                width: 0;
                height: 0;
                pointer-events: none;
            }}
            
            .btn {{
                padding: 10px 24px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                display: inline-block;
            }}
            
            .btn-primary {{
                background: #3b82f6;
                color: white;
            }}
            
            .btn-primary:hover {{
                background: #2563eb;
            }}
            
            .btn-secondary {{
                background: #6b7280;
                color: white;
            }}
            
            .btn-secondary:hover {{
                background: #4b5563;
            }}
            
            .table-section {{
                margin-top: 40px;
            }}
            
            .table-section h2 {{
                font-size: 18px;
                color: #1a1a1a;
                margin-bottom: 16px;
                font-weight: 600;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            th {{
                text-align: left;
                padding: 12px;
                border-bottom: 2px solid #e5e7eb;
                color: #1a1a1a;
                font-weight: 600;
                font-size: 14px;
            }}
            
            td {{
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
                color: #1a1a1a;
                font-size: 14px;
            }}
            
            tr:hover {{
                background: #fafafa;
            }}
            
            .alert {{
                padding: 12px 16px;
                border-radius: 6px;
                margin-bottom: 20px;
                display: none;
                font-size: 14px;
            }}
            
            .alert.show {{
                display: block;
            }}
            
            .alert-success {{
                background: #d1fae5;
                color: #065f46;
                border-left: 4px solid #22c55e;
            }}
            
            .alert-error {{
                background: #fee2e2;
                color: #991b1b;
                border-left: 4px solid #ef4444;
            }}
            
            .alert-info {{
                background: #dbeafe;
                color: #1e40af;
                border-left: 4px solid #3b82f6;
            }}
            
            .bot-selector {{
                margin-bottom: 30px;
            }}
            
            .bot-selector label {{
                display: block;
                font-size: 14px;
                color: #1a1a1a;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .bot-selector input,
            .bot-selector select {{
                width: 100%;
                max-width: 500px;
                padding: 10px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }}
            
            .bot-selector input:focus,
            .bot-selector select:focus {{
                outline: none;
                border-color: #3b82f6;
            }}
            
            .actions {{
                display: flex;
                gap: 12px;
                margin-top: 16px;
            }}
            
            .loading {{
                display: none;
                text-align: center;
                padding: 40px;
            }}
            
            .loading.show {{
                display: block;
            }}
            
            .spinner {{
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3b82f6;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 12px;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>CSV Data Manager</h1>
            
            <div id="alert" class="alert"></div>
            
            <div class="bot-selector">
                <label for="botId">Bot ID</label>
                <input type="text" id="botId" placeholder="Enter or paste bot UUID" list="botList" />
                <datalist id="botList"></datalist>
                <button class="btn btn-secondary" onclick="loadBotData()" style="margin-top: 8px;">Load Bot Data</button>
            </div>
            
            <div class="status-section">
                <h2>Current Data Status</h2>
                <div id="statusInfo">
                    <div id="loading" class="loading">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                    <div id="fileStatus" class="status-info"></div>
                    <div id="uploadMeta" class="status-meta"></div>
                </div>
            </div>
            
            <div class="upload-section" id="uploadZone">
                <h3>Upload New CSV File</h3>
                <p>This will replace the existing data</p>
                <input type="file" id="fileInput" class="file-input" accept=".csv" />
                <div class="file-upload-area">
                    <button class="btn btn-primary" onclick="selectFile()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px; vertical-align: middle;">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="17 8 12 3 7 8"></polyline>
                            <line x1="12" y1="3" x2="12" y2="15"></line>
                        </svg>
                        Choose File
                    </button>
                    <span id="fileName" style="margin-left: 12px; color: #666;">No file chosen</span>
                </div>
                <button class="btn btn-primary" onclick="uploadCSV()" style="margin-top: 12px;">Upload CSV File</button>
            </div>
            
            <div class="actions">
                <button class="btn btn-primary" onclick="downloadCSV()">Download CSV</button>
            </div>
            
            <div class="table-section" id="tableSection">
                <h2>Current Data (First 10 rows)</h2>
                <table id="dataTable">
                    <thead id="tableHead"></thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>
        
        <script>
            let selectedFile = null;
            
            // Load available bots from API
            async function loadBots() {{
                try {{
                    const response = await fetch('/api/v1/bot_hub/');
                    
                    if (!response.ok) {{
                        throw new Error('Failed to load bots');
                    }}
                    
                    const data = await response.json();
                    // Handle both array and object responses
                    const bots = Array.isArray(data) ? data : (data.bots || []);
                    const botDatalist = document.getElementById('botList');
                    
                    // Clear existing options
                    botDatalist.innerHTML = '';
                    
                    // Add bot options to datalist
                    bots.forEach(bot => {{
                        const option = document.createElement('option');
                        option.value = bot.id;
                        option.textContent = `${{bot.name}} (${{bot.id}})`;
                        botDatalist.appendChild(option);
                    }});
                    
                    // Auto-fill with first bot if available and input is empty
                    const botInput = document.getElementById('botId');
                    if (bots.length > 0 && !botInput.value) {{
                        botInput.value = bots[0].id;
                        loadBotData();
                    }}
                }} catch (error) {{
                    console.error('Error loading bots:', error);
                    showAlert('Failed to load bots: ' + error.message, 'error');
                }}
            }}
            
            function loadBotData() {{
                loadStats();
            }}
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {{
                loadBots();
            }});
            
            // Bot ID change - removed duplicate event listener since we now use onchange in HTML
            
            // Upload zone interactions
            const uploadZone = document.getElementById('uploadZone');
            const fileInput = document.getElementById('fileInput');
            
            // Don't trigger file selector when clicking on buttons inside uploadZone
            uploadZone.addEventListener('click', (e) => {{
                // Only open file selector if clicking the zone itself, not buttons
                if (e.target === uploadZone || e.target.tagName === 'H3' || e.target.tagName === 'P') {{
                    fileInput.click();
                }}
            }});
            
            uploadZone.addEventListener('dragover', (e) => {{
                e.preventDefault();
                uploadZone.classList.add('drag-over');
            }});
            
            uploadZone.addEventListener('dragleave', () => {{
                uploadZone.classList.remove('drag-over');
            }});
            
            uploadZone.addEventListener('drop', (e) => {{
                e.preventDefault();
                uploadZone.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0) {{
                    selectedFile = files[0];
                    document.getElementById('fileName').textContent = selectedFile.name;
                    showAlert('File selected: ' + selectedFile.name, 'info');
                }}
            }});
            
            fileInput.addEventListener('change', (e) => {{
                if (e.target.files.length > 0) {{
                    selectedFile = e.target.files[0];
                    document.getElementById('fileName').textContent = selectedFile.name;
                    showAlert('File selected: ' + selectedFile.name, 'info');
                }}
            }});
            
            function selectFile() {{
                fileInput.click();
            }}
            
            function getBotId() {{
                const botId = document.getElementById('botId').value.trim();
                if (!botId) {{
                    showAlert('Please enter a Bot ID', 'error');
                    return null;
                }}
                return botId;
            }}
            
            async function loadStats() {{
                const botId = getBotId();
                if (!botId) return;
                
                document.getElementById('loading').classList.add('show');
                document.getElementById('fileStatus').innerHTML = '';
                document.getElementById('uploadMeta').innerHTML = '';
                document.getElementById('tableBody').innerHTML = '';
                document.getElementById('tableHead').innerHTML = '';
                
                try {{
                    const response = await fetch(`/csv_manager/stats?bot_id=${{botId}}`);
                    const data = await response.json();
                    
                    if (response.ok) {{
                        // Update status
                        document.getElementById('fileStatus').innerHTML = 
                            `Data loaded: ${{data.total_users}} rows, ${{data.total_fields}} columns`;
                        document.getElementById('uploadMeta').innerHTML = 
                            `Provider: {provider_name.upper()}`;
                        
                        // Load preview data
                        await loadPreview(botId);
                    }} else {{
                        showAlert('Failed to load stats: ' + data.detail, 'error');
                    }}
                }} catch (error) {{
                    showAlert('Error loading stats: ' + error.message, 'error');
                }} finally {{
                    document.getElementById('loading').classList.remove('show');
                }}
            }}
            
            async function loadPreview(botId) {{
                try {{
                    const response = await fetch(`/csv_manager/preview?bot_id=${{botId}}`);
                    const data = await response.json();
                    
                    if (response.ok && data.users.length > 0) {{
                        // Get all columns
                        const allColumns = new Set(['user_id']);
                        data.users.forEach(user => {{
                            Object.keys(user.data).forEach(key => allColumns.add(key));
                        }});
                        const columns = Array.from(allColumns);
                        
                        // Create table header
                        const thead = document.getElementById('tableHead');
                        const headerRow = document.createElement('tr');
                        columns.forEach(col => {{
                            const th = document.createElement('th');
                            th.textContent = col;
                            headerRow.appendChild(th);
                        }});
                        thead.appendChild(headerRow);
                        
                        // Create table body
                        const tbody = document.getElementById('tableBody');
                        data.users.slice(0, 10).forEach(user => {{
                            const row = document.createElement('tr');
                            columns.forEach(col => {{
                                const td = document.createElement('td');
                                if (col === 'user_id') {{
                                    td.textContent = user.user_id;
                                }} else {{
                                    td.textContent = user.data[col] || '';
                                }}
                                row.appendChild(td);
                            }});
                            tbody.appendChild(row);
                        }});
                    }}
                }} catch (error) {{
                    console.error('Error loading preview:', error);
                }}
            }}
            
            async function uploadCSV() {{
                const botId = getBotId();
                if (!botId) return;
                
                if (!selectedFile) {{
                    showAlert('Please select a CSV file first', 'error');
                    return;
                }}
                
                const formData = new FormData();
                formData.append('file', selectedFile);
                
                document.getElementById('loading').classList.add('show');
                
                try {{
                    const response = await fetch(
                        `/csv_manager/upload?bot_id=${{botId}}&replace=true`,
                        {{
                            method: 'POST',
                            body: formData
                        }}
                    );
                    
                    const data = await response.json();
                    
                    if (response.ok) {{
                        let message = `Success! Added: ${{data.users_added}}, Updated: ${{data.users_updated}}`;
                        if (data.errors.length > 0) {{
                            message += ` (Errors: ${{data.errors.length}})`;
                        }}
                        showAlert(message, 'success');
                        loadStats();  // Refresh
                    }} else {{
                        showAlert('Upload failed: ' + data.detail, 'error');
                    }}
                }} catch (error) {{
                    showAlert('Error uploading CSV: ' + error.message, 'error');
                }} finally {{
                    document.getElementById('loading').classList.remove('show');
                }}
            }}
            
            async function downloadCSV() {{
                const botId = getBotId();
                if (!botId) return;
                
                try {{
                    const response = await fetch(`/csv_manager/export?bot_id=${{botId}}`);
                    
                    if (response.ok) {{
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `bot_${{botId}}_users.csv`;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        showAlert('CSV exported successfully!', 'success');
                    }} else {{
                        const data = await response.json();
                        showAlert('Export failed: ' + data.detail, 'error');
                    }}
                }} catch (error) {{
                    showAlert('Error exporting CSV: ' + error.message, 'error');
                }}
            }}
            
            function showAlert(message, type) {{
                const alert = document.getElementById('alert');
                alert.textContent = message;
                alert.className = `alert alert-${{type}} show`;
                
                setTimeout(() => {{
                    alert.classList.remove('show');
                }}, 5000);
            }}
        </script>
    </body>
    </html>
    """

    return html_content


@router.get("/stats", response_model=StatsResponse)
async def get_stats(bot_id: UUID = Query(..., description="Bot UUID")):
    """Get user data statistics."""
    try:
        stats = await CSVManagerService.get_user_data_stats(bot_id)
        stats["provider"] = settings.hub_config.userdata_provider.value
        return stats
    except Exception as e:
        logger.error(f"Error getting stats for bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview")
async def get_preview(bot_id: UUID = Query(..., description="Bot UUID")):
    """Get preview of user data (first 10 rows)."""
    try:
        from bot.bot_hub.hub import BotHub

        bot_hub = BotHub(bot_id)
        user_data_list = await bot_hub.userdata_provider.list_user_data()

        users = [
            {"user_id": user_data.user_id, "data": user_data.data}
            for user_data in user_data_list
        ]

        return {"users": users[:10]}
    except Exception as e:
        logger.error(f"Error getting preview for bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    bot_id: UUID = Query(..., description="Bot UUID"),
    replace: bool = Query(False, description="Replace all existing data"),
    file: UploadFile = File(..., description="CSV file to upload"),
):
    """Upload CSV file with user data."""
    try:
        # Read CSV content
        csv_content = (await file.read()).decode("utf-8")

        # Import users
        result = await CSVManagerService.import_users_from_csv(
            bot_id, csv_content, replace
        )

        return result
    except Exception as e:
        logger.error(f"Error uploading CSV for bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_csv(bot_id: UUID = Query(..., description="Bot UUID")):
    """Export user data as CSV file."""
    try:
        csv_content = await CSVManagerService.export_users_to_csv(bot_id)

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=bot_{bot_id}_users.csv"
            },
        )
    except Exception as e:
        logger.error(f"Error exporting CSV for bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_all_users(bot_id: UUID = Query(..., description="Bot UUID")):
    """Clear all users for a bot."""
    try:
        deleted_count = await CSVManagerService.clear_all_users(bot_id)
        return {"success": True, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Error clearing users for bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
