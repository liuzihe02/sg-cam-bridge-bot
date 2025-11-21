# Singapore Bridge Bot - Setup Guide

## Quick Start (Local Testing)

### Prerequisites

1. **Install uv** (fast Python package manager):
   ```bash
   # macOS/Linux:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Node.js** (for frontend): https://nodejs.org

### Step 1: Get Telegram Bot Token FIRST

You need this before anything else!

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow prompts:
   - Name: `SG Bridge Bot` (or your choice)
   - Username: `yourname_bridge_bot` (must end in 'bot')
4. **Copy the token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Backend Setup

```bash
cd backend

# Create .env file with your token
cat > .env << EOF
TELEGRAM_TOKEN=paste_your_token_here
MINI_APP_URL=http://localhost:5173
EOF

# Install dependencies with uv (creates .venv automatically)
uv pip install -r requirements.txt
```

**That's it!** uv auto-creates a `.venv` folder and installs everything.

### Step 3: Frontend Setup

```bash
cd frontend
# Install dependencies
npm install
```

### Step 4: Run Both Servers

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

✅ Backend: http://localhost:8000
✅ Frontend: http://localhost:5173

### Step 5: Test Locally with ngrok

```bash
# Install ngrok: https://ngrok.com/download

# Expose backend
ngrok http 8000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Set webhook:
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d "url=https://abc123.ngrok.io/api/webhook"
```

Now you can test in Telegram:
- Create a group
- Add your bot
- Send `/start`

---

## Production Deployment (Railway)

### 1. Prepare for Deployment

```bash
# Build frontend
cd frontend
npm run build

# This creates frontend/dist/ folder
```

### 2. Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Create new project: "New Project" → "Deploy from GitHub repo"
4. Select your repository

### 3. Configure Environment Variables

In Railway dashboard → Variables:
```
TELEGRAM_TOKEN=your_actual_bot_token
MINI_APP_URL=https://your-app.up.railway.app
PORT=8000
```

### 4. Deploy

Railway will automatically:
- Detect Python project
- Install dependencies from requirements.txt
- Run the Procfile command
- Assign a public URL

### 5. Set Telegram Webhook

Once deployed, get your Railway URL (e.g., `https://bridge-bot-production.up.railway.app`):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d "url=https://bridge-bot-production.up.railway.app/api/webhook"
```

### 6. Create Mini App

Message @BotFather:
```
/newapp
Select bot: @your_bot_name
Name: Singapore Bridge
Description: Play bridge with friends
URL: https://bridge-bot-production.up.railway.app
```

Upload a 512x512 PNG icon (playing cards image).

### 7. Test

1. Create Telegram group
2. Add bot to group
3. Send `/start`
4. Click "Join Game" 4 times (or add AI)
5. Click "🎮 Open Game"

---

## Troubleshooting

### "Game not found" error
- Check Railway logs for backend errors
- Verify webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- Make sure MINI_APP_URL matches your Railway URL

### Frontend can't reach backend
- Update `MINI_APP_URL` in Railway variables
- Redeploy after changing environment variables

### Cards not showing as valid/invalid
- Check browser console for errors
- Verify game state in `/api/game` endpoint

### Webhook not receiving updates
- Verify webhook URL is correct
- Check Railway logs for incoming requests
- Make sure URL is HTTPS (not HTTP)

---

## Development Tips

### View logs in Railway
- Go to your project → Deployments → Click latest deployment
- View real-time logs in the terminal

### Reset game during development
- Send `/stop` in Telegram group
- Send `/start` to create new game

### Test with AI players
- Click "Add AI" button 3 times
- Click "Join Game" once (you + 3 AI)

### Debug backend locally
```bash
cd backend
source .venv/bin/activate
python main.py
# Add print statements in bridge.py or main.py
```

### Debug frontend locally
- Open browser console (F12)
- Check Network tab for API calls
- Add console.log in components

---

## Project Structure

```
sg-cam-bridge-bot/
├── backend/
│   ├── main.py              # FastAPI app + Telegram webhook
│   ├── bridge.py            # Game logic
│   ├── telegram_bot.py      # Bot helpers
│   ├── requirements.txt
│   ├── Procfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React app
│   │   ├── main.tsx         # Entry point
│   │   ├── types.ts         # TypeScript interfaces
│   │   ├── api.ts           # Backend API calls
│   │   ├── styles.css       # Styling
│   │   └── components/      # React components
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── spec.md                  # Full specification
└── README.md
```

---

## Next Steps

1. Test locally with 4 browser tabs
2. Invite friends to test
3. Monitor Railway logs for errors
4. Add features (scoring, game history, etc.)

Enjoy your bridge game! 🃏
