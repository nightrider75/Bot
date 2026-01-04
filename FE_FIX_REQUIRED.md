# **FRONTEND FIX REQUIRED** ⚠️

## The Real Issue:
WebSocket protocol doesn't properly support `Authorization` headers during the handshake. The header is being sent but **rejected by the websockets library** before reaching our code.

## ✅ SOLUTION: Pass Auth via Query Parameter

### What FE Developer Needs to Change:

**OLD CODE:**
```javascript
const ws = new WebSocket(fullUrl);
```

**NEW CODE:**
```javascript
// Add auth token to URL
const authToken = btoa('admin:admin'); // Base64 encode username:password
const separator = fullUrl.includes('?') ? '&' : '?';
const wsUrlWithAuth = `${fullUrl}${separator}auth_token=${authToken}`;

const ws = new WebSocket(wsUrlWithAuth);
```

### Complete Example for `websocket_test.html`:

```javascript
function connectWebSocket() {
    const websocketUrl = document.getElementById('websocketUrl').value.trim();
    const userId = document.getElementById('selectedUserId').value.trim();
    
    if (!websocketUrl) {
        alert('Please enter a WebSocket URL');
        return;
    }
    
    // Build WebSocket URL with parameters
    const urlParams = new URLSearchParams();
    urlParams.set('user_id', userId);
    
    // ADD THIS: Include auth token
    const authToken = btoa('admin:admin'); // username:password
    urlParams.set('auth_token', authToken);
    
    // Add any additional parameters from URL if needed
    const currentUrlParams = new URLSearchParams(window.location.search);
    const agentEnabled = currentUrlParams.get('agent_enabled');
    if (agentEnabled) {
        urlParams.set('agent_enabled', agentEnabled);
    }
    
    // Construct the full WebSocket URL with query parameters
    const separator = websocketUrl.includes('?') ? '&' : '?';
    const fullUrl = `${websocketUrl}${separator}${urlParams.toString()}`;
    console.log('Connecting to WebSocket:', fullUrl);
    
    ws = new WebSocket(fullUrl);
    ws.binaryType = 'arraybuffer';
    // ... rest of code
}
```

### That's It!
Just add `auth_token` to the query string with Base64 encoded `username:password`.

