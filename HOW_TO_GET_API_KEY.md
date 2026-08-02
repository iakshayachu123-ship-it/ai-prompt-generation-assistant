# How to Get Your Anthropic API Key - Step by Step Guide

## Step 1: Go to Anthropic Console
1. Open your web browser
2. Go to: **https://console.anthropic.com/**
3. You'll see the Anthropic login/signup page

## Step 2: Create an Account (if you don't have one)
1. Click **"Sign Up"** or **"Get Started"**
2. Enter your email address
3. Create a password
4. Verify your email (check your inbox)
5. Complete the signup process

## Step 3: Navigate to API Keys
1. After logging in, you'll see the Anthropic Console dashboard
2. Look for **"API Keys"** in the left sidebar menu
3. Click on **"API Keys"**

## Step 4: Create a New API Key
1. Click the **"Create Key"** button (usually at the top right)
2. Give your key a name (e.g., "Photo Prompt App")
3. Click **"Create Key"** or **"Generate"**
4. **IMPORTANT**: Copy the key immediately - you'll only see it once!
   - The key will look like: `sk-ant-api03-xxxxxxxxxxxxx...`
   - It starts with `sk-ant-`

## Step 5: Add the Key to Your Project
1. Open `photo_prompt_project/settings.py` in your code editor
2. Find line 139 (look for `ANTHROPIC_API_KEY`)
3. Replace `'YOUR_API_KEY_HERE'` with your actual key
4. It should look like:
   ```python
   ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', 'sk-ant-api03-your-actual-key-here')
   ```
5. Save the file

## Step 6: Restart Your Server
1. Stop your Django server (press Ctrl+C in the terminal)
2. Start it again: `python manage.py runserver`

## That's it! Your app should now work.

---

## Troubleshooting

**Q: I can't find the API Keys section**
- Make sure you're logged in
- Look in the left sidebar or top navigation
- Try: https://console.anthropic.com/settings/keys

**Q: I lost my API key**
- Go back to API Keys section
- You can create a new one (old ones won't work after creation)
- Delete the old one if needed

**Q: Do I need to pay?**
- Anthropic offers free credits to start
- Check their pricing: https://www.anthropic.com/pricing
- You'll get some free usage when you sign up

**Q: The key doesn't work**
- Make sure you copied the ENTIRE key (they're long)
- Check there are no extra spaces
- Make sure it's inside quotes: `'sk-ant-...'`
- Restart your server after adding the key


