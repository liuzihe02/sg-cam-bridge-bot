# **Singapore Bridge Telegram Bot + Mini App - Implementation Specification**

## **Project Overview**

Build a turn-based card game (Singapore Bridge) playable via Telegram with 4 players (humans or AI). Users start games with `/start` command, join via inline buttons, and play through a visual Mini App interface.

**Target:** 20 users max (friends)  
**Priority:** Simplicity over features  
**Timeline:** ~10-12 hours of focused development

---

## **Architecture Decision**

### **Platform: Railway (Not Vercel)**

**Why Railway:**
- ✅ Python runs as persistent process (not serverless)
- ✅ No cold starts
- ✅ Natural FastAPI app structure
- ✅ Simpler mental model
- ✅ Better for Python backends

### **Storage: In-Memory Dict (Not Redis)**

**Why in-memory:**
- ✅ Railway = persistent process (survives between requests)
- ✅ 20 users = games happen in sessions
- ✅ Service restart = rare, just restart game
- ✅ Zero external dependencies
- ✅ Way simpler code

**Trade-off accepted:** Game state lost on deploy/restart (acceptable for casual play)

---

## **Tech Stack**

```
Backend:   Python 3.11 + FastAPI + python-telegram-bot
Frontend:  React 18 + TypeScript + Vite
Storage:   In-memory Python dict
Hosting:   Railway (single service, serves both bot + frontend)
```

---

## **Project Structure**

```
bridge-bot/
├── backend/
│   ├── main.py              # FastAPI app (~200 lines)
│   ├── bridge.py            # Game logic (adapt from existing)
│   ├── telegram_bot.py      # Bot helpers (~50 lines)
│   ├── requirements.txt
│   └── Procfile
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx         # Entry (~15 lines)
│   │   ├── App.tsx          # Main game (~150 lines)
│   │   ├── types.ts         # TypeScript interfaces (~50 lines)
│   │   ├── api.ts           # Backend calls (~50 lines)
│   │   ├── styles.css       # Minimal styling (~150 lines)
│   │   └── components/
│   │       ├── GameInfo.tsx # Top bar (~30 lines)
│   │       ├── Trick.tsx    # Current trick (~40 lines)
│   │       ├── Hand.tsx     # Player cards (~50 lines)
│   │       ├── BidPanel.tsx # Bidding UI (~40 lines)
│   │       └── CallPanel.tsx # Partner selection (~40 lines)
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
└── README.md
```

**Total code:** ~850 lines

---

## **Singapore Bridge Rules** (Implementation Reference)

### **Game Phases**

1. **JOIN**: Waiting for 4 players
2. **BID**: Clockwise bidding until 3 passes
3. **CALL**: Winner picks partner card
4. **PLAY**: 13 tricks of card play
5. **END**: Show winner

### **Bidding Rules**

- Format: `1C`, `1D`, `1H`, `1S`, `1N`, `2C`, ..., `7N`
- Suit order: ♣ < ♦ < ♥ < ♠ < NT
- Must bid higher than previous
- "PASS" = don't bid
- 3 consecutive passes after bid = bidding ends
- Bid number = tricks needed (e.g., `2H` = 8 tricks, `7N` = 13 tricks)

### **Partner Selection**

- Declarer calls card they DON'T have (e.g., "Ace of Spades")
- Holder of that card is secret partner
- Partner reveals by playing the called card
- Declarer can call card they DO have (play alone)

### **Card Play Rules**

- Player left of declarer leads first (unless No Trump, then declarer leads)
- Must follow suit if possible
- Can't lead trump until "broken" (someone played trump on non-trump trick)
- Exception: Can lead trump if only trump cards left
- Trick winner leads next trick

### **Playable Hand (Wash)**

Calculate hand points:
- A=4, K=3, Q=2, J=1
- +1 per card after 4th in each suit
- Example: `♠AKQ7532` = 4+3+2+3 = 12 points (3 extra spades)

If ANY player has <4 points, reshuffle ("wash")

### **Scoring**

- Points = 2^(bid-1): [1, 2, 4, 8, 16, 32, 64] for bids 1-7
- Declarer + partner get points if they make contract
- Opponents get points if contract fails
- No overtrick bonuses

---

## **Data Models**

### **Game State (In-Memory)**

```python
# In main.py
games: Dict[str, Game] = {}  # Key = chat_id

class Game:
    id: str                      # chat_id
    players: List[Player]        # Always 4, [0] leads current trick
    phase: int                   # 0=JOIN, 1=BID, 2=CALL, 3=PLAY, 4=END
    activePlayer: Player         # Current turn
    
    # Bidding
    bid: str                     # 'PASS', '1C', '2H', etc.
    bidder: Player | None        # Highest bidder
    
    # Partner
    partnerCard: str | None      # 'SA', 'HK', etc.
    partner: Player | None       # Revealed when card played
    
    # Playing
    trump: str                   # 'C', 'D', 'H', 'S', '' (NT)
    contract: int                # 7-13 tricks needed
    currentTrick: List[str|None] # 4 cards [None, 'SA', None, 'H7']
    trumpBroken: bool
    currentSuit: str | None      # Lead suit of trick
    
    # Tracking
    sets: List[int]              # Tricks won [2, 3, 4, 4]

class Player:
    id: str                      # Telegram user_id (string)
    name: str                    # first_name
    hand: List[str]              # ['SA', 'HK', 'D7', ...]
    isAI: bool
    tricks: int                  # Tricks won this game
    game: Game                   # Back-reference
```

### **Card Format**

- `'SA'` = Spade Ace
- `'HK'` = Heart King  
- `'D7'` = Diamond 7
- `'CT'` = Club 10 (T=10)

**Suits:** `C` (♣), `D` (♦), `H` (♥), `S` (♠)  
**Values:** `A K Q J T 9 8 7 6 5 4 3 2`

### **Frontend Types**

```typescript
// types.ts
interface GameState {
  phase: 'JOIN' | 'BID' | 'CALL' | 'PLAY' | 'END';
  activePlayerId: string;
  players: Player[];
  hand: string[];              // Player's cards
  validCards: string[];        // Playable cards
  validBids: string[];         // Available bids
  currentTrick: (string | null)[];
  trump: string;               // 'C' | 'D' | 'H' | 'S' | ''
  contract: number;
  declarer: { id: string; name: string } | null;
  partnerCard: string | null;
}

interface Player {
  id: string;
  name: string;
  tricks: number;
}
```

---

## **Backend Implementation**

### **File: `backend/main.py`**

```python
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict
import asyncio
import os

from bridge import Game, Player
from telegram_bot import bot, get_join_keyboard

app = FastAPI()

# ============ IN-MEMORY STORAGE ============
games: Dict[str, Game] = {}

# ============ SERVE FRONTEND ============
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/")
async def root():
    return FileResponse('frontend/dist/index.html')

# ============ GAME API ============

@app.get("/api/game")
async def get_game(chat_id: str, user_id: str):
    """Get game state for player"""
    if chat_id not in games:
        raise HTTPException(404, "Game not found")
    
    game = games[chat_id]
    player = next((p for p in game.players if p.id == user_id), None)
    if not player:
        raise HTTPException(404, "Player not in game")
    
    return {
        'phase': ['JOIN', 'BID', 'CALL', 'PLAY', 'END'][game.phase],
        'activePlayerId': game.activePlayer.id if game.activePlayer else None,
        'players': [{'id': p.id, 'name': p.name, 'tricks': p.tricks} 
                    for p in game.players],
        'hand': player.hand,
        'validCards': player.valid_cards() if game.phase == 3 else [],
        'validBids': list(game.valid_bids()) if game.phase == 1 else [],
        'currentTrick': game.currentTrick,
        'trump': game.trump,
        'contract': game.contract,
        'declarer': {'id': game.declarer.id, 'name': game.declarer.name} 
                    if game.declarer else None,
        'partnerCard': game.partnerCard
    }

@app.post("/api/bid")
async def make_bid(data: dict):
    """Handle player bid"""
    game = games[data['chat_id']]
    player = next(p for p in game.players if p.id == data['user_id'])
    
    if player != game.activePlayer:
        raise HTTPException(400, "Not your turn")
    
    player.make_bid(data['bid'])
    await process_ai_turns(game)
    
    return {'success': True}

@app.post("/api/call")
async def call_partner(data: dict):
    """Declarer picks partner card"""
    game = games[data['chat_id']]
    player = next(p for p in game.players if p.id == data['user_id'])
    
    if player != game.activePlayer:
        raise HTTPException(400, "Not your turn")
    
    player.call_partner(data['card'])
    await process_ai_turns(game)
    
    return {'success': True}

@app.post("/api/play")
async def play_card(data: dict):
    """Play a card"""
    game = games[data['chat_id']]
    player = next(p for p in game.players if p.id == data['user_id'])
    
    if player != game.activePlayer:
        raise HTTPException(400, "Not your turn")
    
    player.play_card(data['card'])
    
    # Check if trick complete
    if all(game.currentTrick):
        game.complete_trick()
    
    await process_ai_turns(game)
    
    return {'success': True}

# ============ TELEGRAM WEBHOOK ============

@app.post("/api/webhook")
async def telegram_webhook(update: dict):
    """Handle Telegram updates"""
    if 'message' in update:
        msg = update['message']
        chat_id = str(msg['chat']['id'])
        text = msg.get('text', '')
        
        if text == '/start':
            # Create new game
            game = Game(chat_id)
            games[chat_id] = game
            
            await bot.send_message(
                chat_id=chat_id,
                text="🃏 *Singapore Bridge Game*\n\nWaiting for 4 players...",
                parse_mode='Markdown',
                reply_markup=get_join_keyboard()
            )
        
        elif text == '/stop':
            if chat_id in games:
                del games[chat_id]
                await bot.send_message(chat_id=chat_id, text="Game stopped.")
    
    elif 'callback_query' in update:
        query = update['callback_query']
        chat_id = str(query['message']['chat']['id'])
        user = query['from_user']
        action = query['data']
        
        if chat_id not in games:
            await bot.answer_callback_query(query['id'], "Game not found")
            return {'ok': True}
        
        game = games[chat_id]
        
        if action == 'join':
            success = game.add_human(str(user['id']), user['first_name'])
            if not success:
                await bot.answer_callback_query(query['id'], "Can't join")
                return {'ok': True}
            
            # Update join message
            player_list = '\n'.join([f"🃏 {p.name}" for p in game.players])
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=query['message']['message_id'],
                text=f"🃏 *Singapore Bridge Game*\n\n*Players:*\n{player_list}\n\n"
                     f"Waiting for {4 - len(game.players)} more...",
                parse_mode='Markdown',
                reply_markup=get_join_keyboard() if not game.full() else None
            )
            
            if game.full():
                await start_game(game)
        
        elif action == 'add_ai':
            game.add_AI()
            if game.full():
                await start_game(game)
        
        await bot.answer_callback_query(query['id'])
    
    return {'ok': True}

# ============ HELPERS ============

async def start_game(game: Game):
    """Start game once 4 players joined"""
    game.start()
    
    # Send Mini App button to chat
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🎮 Open Game",
            web_app=WebAppInfo(url=os.environ.get('MINI_APP_URL'))
        )
    ]])
    
    await bot.send_message(
        chat_id=game.id,
        text="🃏 Game starting!\n\nClick below to play:",
        reply_markup=keyboard
    )
    
    # DM each player their hand
    for player in game.players:
        if not player.isAI:
            await bot.send_message(
                chat_id=player.id,
                text=f"Game started! Your hand:\n{format_hand(player.hand)}"
            )

async def process_ai_turns(game: Game):
    """Process all consecutive AI turns"""
    while game.activePlayer and game.activePlayer.isAI and game.phase != 4:
        await asyncio.sleep(0.5)  # Small delay
        
        if game.phase == 1:  # BID
            game.activePlayer.make_bid()
        elif game.phase == 2:  # CALL
            game.activePlayer.call_partner()
        elif game.phase == 3:  # PLAY
            game.activePlayer.play_card()
            if all(game.currentTrick):
                game.complete_trick()

def format_hand(hand: List[str]) -> str:
    """Format hand for Telegram message"""
    suits = {'C': '♣', 'D': '♦', 'H': '♥', 'S': '♠'}
    grouped = {}
    for card in hand:
        suit = card[0]
        grouped.setdefault(suit, []).append(card[1])
    
    lines = []
    for suit in 'CDHS':
        if suit in grouped:
            cards = ' '.join(grouped[suit]).replace('T', '10')
            lines.append(f"{suits[suit]} {cards}")
    
    return '\n'.join(lines)
```

### **File: `backend/telegram_bot.py`**

```python
import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

bot = Bot(token=os.environ.get('TELEGRAM_TOKEN'))

def get_join_keyboard():
    """Return inline keyboard for joining game"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Join Game", callback_data="join"),
            InlineKeyboardButton("Add AI", callback_data="add_ai")
        ]
    ])
```

### **File: `backend/bridge.py`**

**Use existing code from your repo with these modifications:**

```python
# CRITICAL CHANGES:

# 1. Remove global Game.games dictionary
# OLD: Game.games = {}
# NEW: Games stored in main.py's in-memory dict

# 2. Ensure player.game is set after deserialization
# In Game.from_dict():
game = cls(data['id'])
# ... populate fields ...
for player in game.players:
    player.game = game  # CRITICAL: Set back-reference
return game

# 3. Make sure valid_cards() works correctly
def valid_cards(self):
    """Return list of playable cards"""
    game = self.game
    hand = self.hand
    
    if not game.currentTrick[0]:  # Leading
        result = hand
        if game.trump and not game.trumpBroken:
            result = [c for c in hand if c[0] != game.trump]
        return result if result else hand
    
    # Following
    lead_suit = game.currentTrick[0][0]
    same_suit = [c for c in hand if c[0] == lead_suit]
    return same_suit if same_suit else hand

# 4. Ensure AI logic is working
# Your existing AI code should work as-is
```

### **File: `backend/requirements.txt`**

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-telegram-bot==21.6
```

### **File: `backend/Procfile`**

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## **Frontend Implementation**

### **File: `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Singapore Bridge</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### **File: `frontend/src/main.tsx`**

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### **File: `frontend/src/types.ts`**

```typescript
export interface GameState {
  phase: 'JOIN' | 'BID' | 'CALL' | 'PLAY' | 'END';
  activePlayerId: string;
  players: Player[];
  hand: string[];
  validCards: string[];
  validBids: string[];
  currentTrick: (string | null)[];
  trump: string;
  contract: number;
  declarer: { id: string; name: string } | null;
  partnerCard: string | null;
}

export interface Player {
  id: string;
  name: string;
  tricks: number;
}
```

### **File: `frontend/src/api.ts`**

```typescript
const API_URL = import.meta.env.PROD 
  ? 'https://your-app.up.railway.app'  // Update after deploy
  : 'http://localhost:8000';

export async function getGame(chatId: string, userId: string) {
  const res = await fetch(
    `${API_URL}/api/game?chat_id=${chatId}&user_id=${userId}`
  );
  if (!res.ok) throw new Error('Failed to get game');
  return res.json();
}

export async function playCard(chatId: string, userId: string, card: string) {
  await fetch(`${API_URL}/api/play`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, user_id: userId, card })
  });
}

export async function makeBid(chatId: string, userId: string, bid: string) {
  await fetch(`${API_URL}/api/bid`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, user_id: userId, bid })
  });
}

export async function callPartner(chatId: string, userId: string, card: string) {
  await fetch(`${API_URL}/api/call`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, user_id: userId, card })
  });
}
```

### **File: `frontend/src/App.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { GameState } from './types';
import { getGame } from './api';
import GameInfo from './components/GameInfo';
import Trick from './components/Trick';
import Hand from './components/Hand';
import BidPanel from './components/BidPanel';
import CallPanel from './components/CallPanel';

// Declare Telegram WebApp
declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        initDataUnsafe: {
          user: { id: number; first_name: string };
          start_param?: string;
        };
      };
    };
  }
}

export default function App() {
  const [game, setGame] = useState<GameState | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    // Get user and chat IDs from Telegram
    const userId = String(tg.initDataUnsafe.user.id);
    const chatId = tg.initDataUnsafe.start_param || String(tg.initDataUnsafe.user.id);

    // Load game initially
    loadGame(chatId, userId);

    // Poll every 2 seconds
    const interval = setInterval(() => {
      loadGame(chatId, userId);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const loadGame = async (chatId: string, userId: string) => {
    try {
      const data = await getGame(chatId, userId);
      setGame(data);
      setError('');
    } catch (err) {
      setError('Failed to load game');
    }
  };

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!game) {
    return <div className="loading">Loading game...</div>;
  }

  const isYourTurn = game.activePlayerId === String(window.Telegram.WebApp.initDataUnsafe.user.id);

  return (
    <div className="app">
      <GameInfo game={game} />
      
      {game.phase === 'PLAY' && (
        <Trick 
          trick={game.currentTrick}
          players={game.players}
          activePlayerId={game.activePlayerId}
        />
      )}

      {game.phase === 'BID' && isYourTurn && (
        <BidPanel validBids={game.validBids} />
      )}

      {game.phase === 'CALL' && isYourTurn && (
        <CallPanel />
      )}

      {game.phase === 'PLAY' && (
        <Hand 
          cards={game.hand}
          validCards={game.validCards}
          disabled={!isYourTurn}
        />
      )}

      {!isYourTurn && game.phase !== 'END' && (
        <div className="waiting">
          Waiting for {game.players.find(p => p.id === game.activePlayerId)?.name}...
        </div>
      )}

      {game.phase === 'END' && (
        <div className="game-over">
          Game Over! Check chat for results.
        </div>
      )}
    </div>
  );
}
```

### **File: `frontend/src/components/GameInfo.tsx`**

```typescript
import { GameState } from '../types';

const SUITS = { C: '♣', D: '♦', H: '♥', S: '♠' };

export default function GameInfo({ game }: { game: GameState }) {
  return (
    <div className="game-info">
      <div>Trump: {game.trump ? SUITS[game.trump as keyof typeof SUITS] : 'NT'}</div>
      <div>Contract: {game.contract}</div>
      {game.declarer && <div>Declarer: {game.declarer.name}</div>}
      {game.partnerCard && <div>Partner: {translateCard(game.partnerCard)}</div>}
    </div>
  );
}

function translateCard(card: string): string {
  const SUITS = { C: '♣', D: '♦', H: '♥', S: '♠' };
  return card[1].replace('T', '10') + SUITS[card[0] as keyof typeof SUITS];
}
```

### **File: `frontend/src/components/Trick.tsx`**

```typescript
import { Player } from '../types';

const SUITS = { C: '♣', D: '♦', H: '♥', S: '♠' };

interface TrickProps {
  trick: (string | null)[];
  players: Player[];
  activePlayerId: string;
}

export default function Trick({ trick, players, activePlayerId }: TrickProps) {
  return (
    <div className="trick">
      {trick.map((card, i) => (
        <div 
          key={i}
          className={`trick-card ${players[i]?.id === activePlayerId ? 'active' : ''}`}
        >
          <div className="player-name">{players[i]?.name}</div>
          {card ? (
            <div className="card-display">
              {card[1].replace('T', '10')} {SUITS[card[0] as keyof typeof SUITS]}
            </div>
          ) : (
            <div className="card-placeholder">—</div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### **File: `frontend/src/components/Hand.tsx`**

```typescript
import { playCard } from '../api';

const SUITS = { C: '♣', D: '♦', H: '♥', S: '♠' };

interface HandProps {
  cards: string[];
  validCards: string[];
  disabled: boolean;
}

export default function Hand({ cards, validCards, disabled }: HandProps) {
  const tg = window.Telegram.WebApp;
  const userId = String(tg.initDataUnsafe.user.id);
  const chatId = tg.initDataUnsafe.start_param || userId;

  const grouped: Record<string, string[]> = {};
  cards.forEach(card => {
    const suit = card[0];
    if (!grouped[suit]) grouped[suit] = [];
    grouped[suit].push(card);
  });

  const handlePlay = async (card: string) => {
    if (disabled || !validCards.includes(card)) return;
    await playCard(chatId, userId, card);
  };

  return (
    <div className="hand">
      {Object.entries(grouped).map(([suit, suitCards]) => (
        <div key={suit} className="suit-row">
          <span className="suit-icon">{SUITS[suit as keyof typeof SUITS]}</span>
          <div className="cards">
            {suitCards.map(card => (
              <button
                key={card}
                onClick={() => handlePlay(card)}
                disabled={disabled || !validCards.includes(card)}
                className={`card ${validCards.includes(card) ? 'valid' : 'invalid'}`}
              >
                {card[1].replace('T', '10')}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

### **File: `frontend/src/components/BidPanel.tsx`**

```typescript
import { makeBid } from '../api';

const SUITS = { C: '♣', D: '♦', H: '♥', S: '♠', N: 'NT' };

interface BidPanelProps {
  validBids: string[];
}

export default function BidPanel({ validBids }: BidPanelProps) {
  const tg = window.Telegram.WebApp;
  const userId = String(tg.initDataUnsafe.user.id);
  const chatId = tg.initDataUnsafe.start_param || userId;

  const handleBid = async (bid: string) => {
    await makeBid(chatId, userId, bid);
  };

  return (
    <div className="bid-panel">
      <h3>Make your bid</h3>
      <div className="bids">
        {validBids.includes('PASS') && (
          <button onClick={() => handleBid('PASS')} className="bid-btn pass">
            Pass
          </button>
        )}
        {validBids.filter(b => b !== 'PASS').map(bid => (
          <button 
            key={bid}
            onClick={() => handleBid(bid)}
            className="bid-btn"
          >
            {bid[0]} {SUITS[bid[1] as keyof typeof SUITS]}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### **File: `frontend/src/components/CallPanel.tsx`**

```typescript
import { callPartner } from '../api';

const SUITS = { C: '♣', D: '♦', H: '♥', S: '♠' };
const VALUES = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

export default function CallPanel() {
  const tg = window.Telegram.WebApp;
  const userId = String(tg.initDataUnsafe.user.id);
  const chatId = tg.initDataUnsafe.start_param || userId;

  const handleCall = async (card: string) => {
    await callPartner(chatId, userId, card);
  };

  return (
    <div className="call-panel">
      <h3>Choose your partner's card</h3>
      <div className="card-grid">
        {Object.entries(SUITS).map(([suitCode, suitSymbol]) => (
          <div key={suitCode} className="suit-section">
            <div className="suit-label">{suitSymbol}</div>
            <div className="cards">
              {VALUES.map(value => {
                const card = suitCode + value;
                return (
                  <button
                    key={card}
                    onClick={() => handleCall(card)}
                    className="card"
                  >
                    {value.replace('T', '10')}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### **File: `frontend/src/styles.css`**

```css
:root {
  --bg: var(--tg-theme-bg-color, #fff);
  --text: var(--tg-theme-text-color, #000);
  --button: var(--tg-theme-button-color, #3390ec);
  --button-text: var(--tg-theme-button-text-color, #fff);
  --secondary: var(--tg-theme-secondary-bg-color, #f0f0f0);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  padding: 16px;
}

.app {
  max-width: 480px;
  margin: 0 auto;
}

/* Game Info */
.game-info {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: var(--secondary);
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}

/* Trick Display */
.trick {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 24px;
}

.trick-card {
  padding: 16px;
  background: var(--secondary);
  border-radius: 8px;
  text-align: center;
}

.trick-card.active {
  border: 2px solid var(--button);
}

.player-name {
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 8px;
}

.card-display {
  font-size: 28px;
  font-weight: 600;
}

.card-placeholder {
  font-size: 28px;
  opacity: 0.3;
}

/* Hand */
.hand {
  margin-top: 24px;
}

.suit-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.suit-icon {
  font-size: 24px;
  width: 32px;
  text-align: center;
}

.cards {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.card {
  padding: 8px 12px;
  background: var(--secondary);
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.card.valid {
  background: var(--button);
  color: var(--button-text);
}

.card.valid:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.card:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Bidding */
.bid-panel {
  padding: 16px;
  background: var(--secondary);
  border-radius: 8px;
  margin: 16px 0;
}

.bid-panel h3 {
  margin-bottom: 12px;
  font-size: 16px;
}

.bids {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
  gap: 8px;
}

.bid-btn {
  padding: 12px;
  background: var(--button);
  color: var(--button-text);
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.bid-btn.pass {
  background: var(--secondary);
  color: var(--text);
  border: 1px solid var(--button);
}

/* Call Partner */
.call-panel {
  padding: 16px;
  background: var(--secondary);
  border-radius: 8px;
}

.call-panel h3 {
  margin-bottom: 16px;
}

.card-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suit-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.suit-label {
  font-size: 20px;
  width: 30px;
}

/* States */
.waiting, .loading, .error, .game-over {
  text-align: center;
  padding: 24px;
  font-size: 14px;
}

.error {
  color: #d32f2f;
}
```

### **File: `frontend/package.json`**

```json
{
  "name": "bridge-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.2"
  }
}
```

### **File: `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### **File: `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
});
```

---

## **Deployment Steps**

### **1. Create Railway Account**

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Get $5 free credit

### **2. Setup Telegram Bot**

```bash
# Message @BotFather on Telegram
/newbot
Name: SG Bridge Bot
Username: your_unique_name_bot

# Save token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### **3. Create Mini App**

```bash
# Message @BotFather
/newapp
Select bot: @your_bot_name
Name: Singapore Bridge
Description: Play bridge with friends
URL: https://bridge-bot-production.up.railway.app  # Update after deploy
# Upload icon (512x512 PNG of playing cards)
```

### **4. Deploy to Railway**

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Set env vars in Railway dashboard:
TELEGRAM_TOKEN=your_bot_token
MINI_APP_URL=https://bridge-bot-production.up.railway.app

# Deploy
git add .
git commit -m "Initial commit"
git push railway main
```

### **5. Set Webhook**

```bash
# After deploy, get Railway URL (e.g., https://bridge-bot-production.up.railway.app)
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d "url=https://bridge-bot-production.up.railway.app/api/webhook"
```

### **6. Update Mini App URL**

```bash
# Message @BotFather
/myapps
Select your app
Edit > URL
Enter: https://bridge-bot-production.up.railway.app
```

### **7. Test**

1. Create Telegram group
2. Add bot to group
3. Send `/start`
4. Click "Join Game" 4 times (or add AI)
5. Click "🎮 Open Game" to play

---

## **Testing Checklist**

**Before deploying:**
- [ ] Backend runs locally (`uvicorn main:app --reload`)
- [ ] Frontend runs locally (`npm run dev`)
- [ ] Can create game with `/start`
- [ ] Can join game (4 players or with AI)
- [ ] Game starts automatically when 4 players joined
- [ ] Cards display correctly grouped by suit
- [ ] Bidding works (bid, pass)
- [ ] Partner selection works
- [ ] Valid cards highlighted, invalid grayed out
- [ ] Cards play correctly
- [ ] Trick winner calculated correctly
- [ ] Trump breaking works
- [ ] Game ends and shows result
- [ ] Multiple games in different chats work
- [ ] AI players work

**After deploying:**
- [ ] Webhook set correctly (returns `{"ok": true}`)
- [ ] Bot responds to `/start` in group
- [ ] Mini App button appears
- [ ] Mini App opens in Telegram
- [ ] Game flows work end-to-end

---

## **Quick Development Essentials**

### **Minimal Test Cases**

**5-Minute Manual Test Flow:**
1. **Happy path**: 4 players join → bid 2H → call partner → play 13 tricks → verify winner
2. **AI test**: 1 human + 3 AI → verify AI bids/plays automatically
3. **Pass test**: All players pass on first round → verify bidding continues
4. **Trump breaking**: Try leading trump before it's broken → verify card grayed out
5. **Multi-game**: Start game in 2 different groups → verify no interference

**That's it.** If these 5 work, ship it.

---

### **Core Error Handling**

**Frontend (`api.ts`):**
```typescript
export async function playCard(chatId: string, userId: string, card: string) {
  try {
    const res = await fetch(`${API_URL}/api/play`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, user_id: userId, card })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.message || 'Something went wrong. Try again!');
      throw new Error(err.message);
    }
  } catch (e) {
    console.error('Play card failed:', e);
    // User already saw alert, just log for debugging
  }
}
```

**Backend (`main.py`):**
```python
@app.post("/api/play")
async def play_card(data: dict):
    try:
        if data['chat_id'] not in games:
            raise HTTPException(404, "Game not found. Did it restart?")

        game = games[data['chat_id']]
        player = next((p for p in game.players if p.id == data['user_id']), None)

        if not player:
            raise HTTPException(404, "You're not in this game")

        if player != game.activePlayer:
            raise HTTPException(400, "Not your turn")

        player.play_card(data['card'])

        if all(game.currentTrick):
            game.complete_trick()

        await process_ai_turns(game)
        return {'success': True}

    except Exception as e:
        print(f"❌ Error in play_card: {e}")  # Minimal logging
        raise
```

**Pattern:** Catch errors → show user-friendly message → log for debugging → continue.

---

### **Security: Keep It Simple**

**Approach:** Trust Telegram's authentication. No initData validation needed for friends-only game.

```python
# In main.py - just use the data Telegram gives you
@app.get("/api/game")
async def get_game(chat_id: str, user_id: str):
    # No validation - we trust it came from Telegram
    # TODO: Add initData validation if opening to public
    ...
```

**Why it's fine:**
- Telegram Mini Apps only work inside Telegram (can't fake easily)
- 20 friends won't hack you
- Worst case: someone plays wrong card → just laugh and restart
- Add validation later if needed (10 lines of code)

---

### **Minimal Logging**

**Add to `backend/main.py`:**
```python
import logging
from datetime import datetime

# Simple console logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# Use throughout:
@app.post("/api/webhook")
async def telegram_webhook(update: dict):
    if 'message' in update and update['message'].get('text') == '/start':
        chat_id = str(update['message']['chat']['id'])
        log(f"🎮 Game started in chat {chat_id}")
        ...

    elif 'callback_query' in update:
        user = update['callback_query']['from_user']
        action = update['callback_query']['data']
        log(f"👤 {user['first_name']} pressed {action}")
        ...

async def start_game(game: Game):
    log(f"🃏 Game {game.id} - 4 players ready, dealing cards")
    ...

# In error handlers:
except Exception as e:
    log(f"❌ Error: {e}")
    ...
```

**That's it.** View logs in Railway dashboard when debugging.

---

**Issue: "Game not found" when opening Mini App**

Solution: Make sure `start_param` is set correctly. The Mini App URL should include chat_id.

**Issue: Cards not marked as valid/invalid**

Solution: Check `valid_cards()` implementation in `bridge.py`. Ensure it handles trump breaking and following suit.

**Issue: AI turns not processing**

Solution: Ensure `player.game` is set after `Game.from_dict()` deserialization.

**Issue: Frontend can't reach backend**

Solution: Update `API_URL` in `api.ts` with your Railway URL.

**Issue: Webhook not receiving updates**

Solution: Check Railway logs. Verify webhook URL with:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

---

## **Estimated Timeline**

- **Backend setup**: 2 hours (adapt bridge.py, write main.py)
- **Frontend components**: 4 hours (6 components)
- **Integration**: 2 hours (connect everything, fix bugs)
- **Deployment**: 1 hour (Railway setup, webhook config)
- **Testing**: 2 hours (test with friends, fix issues)

**Total: 10-12 hours**

---

## **Next Steps**

1. Create backend structure
2. Adapt `bridge.py` for in-memory storage
3. Implement FastAPI endpoints
4. Build frontend components
5. Test locally
6. Deploy to Railway
7. Configure Telegram bot + Mini App
8. Play with friends!

---

**This specification is complete and ready for implementation. Hand off to next Claude session.**