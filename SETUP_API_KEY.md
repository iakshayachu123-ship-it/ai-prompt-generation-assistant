# How to Set Up Your Anthropic API Key

## Quick Setup (2 minutes)

1. **Get your API key:**
   - Go to https://console.anthropic.com/
   - Sign up or log in
   - Click on "API Keys" in the menu
   - Click "Create Key"
   - Copy the key (it starts with `sk-ant-...`)

2. **Add it to your project:**
   - Open the file: `photo_prompt_project/settings.py`
   - Find line 137 (look for `ANTHROPIC_API_KEY`)
   - Replace `'YOUR_API_KEY_HERE'` with your actual API key
   - Save the file

3. **Restart your server:**
   - Stop the server (press Ctrl+C)
   - Run: `python manage.py runserver`

## Example

**Before:**
```python
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', 'YOUR_API_KEY_HERE')
```

**After (with your real key):**
```python
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', 'sk-ant-api03-abc123xyz...')
```

That's it! Your app should now work.

