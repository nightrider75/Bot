⚠️ URGENT: Remove PORT from ENV_FILE Secret
=============================================

The ENV_FILE secret in GitHub contains:
```
PORT=8080
```

This is causing a conflict because:
1. Cloud Run sets PORT environment variable automatically
2. Your ENV_FILE also contains PORT=8080
3. This creates confusion about which port to use

FIX:
----
1. Go to GitHub → Settings → Environments → production → ENV_FILE
2. Edit the ENV_FILE secret
3. REMOVE the line: PORT=8080
4. Keep all other lines

Your ENV_FILE should NOT contain the PORT line.

The PORT should only come from Cloud Run's environment variable, which your
app will read automatically through pydantic-settings.

After removing PORT from ENV_FILE:
- Cloud Run will set PORT=8080 (or whatever port it chooses)
- Your app will read that PORT from the environment
- The .env file won't override it
