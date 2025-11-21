from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import asyncio
import os
import logging
from datetime import datetime
from pathlib import Path

from bridge import Game, Player
from telegram_bot import bot, get_join_keyboard
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

app = FastAPI()

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ LOGGING ============
logging.basicConfig(level=logging.INFO, format='%(message)s')

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ============ IN-MEMORY STORAGE ============
games: Dict[str, Game] = {}

# ============ SERVE FRONTEND ============
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/")
    async def root():
        return FileResponse(str(frontend_dist / "index.html"))

# ============ GAME API ============

@app.get("/api/game")
async def get_game(chat_id: str, user_id: str):
    """Get game state for player"""
    try:
        if chat_id not in games:
            raise HTTPException(404, "Game not found. Did it restart?")

        game = games[chat_id]
        player = next((p for p in game.players if p.id == user_id), None)
        if not player:
            raise HTTPException(404, "You're not in this game")

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
            'partnerCard': game.partnerCard,
            'bid': game.bid
        }
    except HTTPException:
        raise
    except Exception as e:
        log(f"❌ Error in get_game: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/bid")
async def make_bid(data: dict):
    """Handle player bid"""
    try:
        chat_id = data['chat_id']
        user_id = data['user_id']
        bid = data['bid']

        if chat_id not in games:
            raise HTTPException(404, "Game not found")

        game = games[chat_id]
        player = next((p for p in game.players if p.id == user_id), None)

        if not player:
            raise HTTPException(404, "Player not in game")

        if player != game.activePlayer:
            raise HTTPException(400, "Not your turn")

        player.make_bid(bid)
        log(f"🃏 Game {chat_id} - {player.name} bid {bid}")

        await process_ai_turns(game)

        return {'success': True}

    except HTTPException:
        raise
    except Exception as e:
        log(f"❌ Error in make_bid: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/call")
async def call_partner(data: dict):
    """Declarer picks partner card"""
    try:
        chat_id = data['chat_id']
        user_id = data['user_id']
        card = data['card']

        if chat_id not in games:
            raise HTTPException(404, "Game not found")

        game = games[chat_id]
        player = next((p for p in game.players if p.id == user_id), None)

        if not player:
            raise HTTPException(404, "Player not in game")

        if player != game.activePlayer:
            raise HTTPException(400, "Not your turn")

        player.call_partner(card)
        log(f"🃏 Game {chat_id} - {player.name} called {card}")

        await process_ai_turns(game)

        return {'success': True}

    except HTTPException:
        raise
    except Exception as e:
        log(f"❌ Error in call_partner: {e}")
        raise HTTPException(500, str(e))


@app.post("/api/play")
async def play_card(data: dict):
    """Play a card"""
    try:
        chat_id = data['chat_id']
        user_id = data['user_id']
        card = data['card']

        if chat_id not in games:
            raise HTTPException(404, "Game not found. Did it restart?")

        game = games[chat_id]
        player = next((p for p in game.players if p.id == user_id), None)

        if not player:
            raise HTTPException(404, "You're not in this game")

        if player != game.activePlayer:
            raise HTTPException(400, "Not your turn")

        player.play_card(card)
        log(f"🃏 Game {chat_id} - {player.name} played {card}")

        # Check if trick complete
        if all(game.currentTrick):
            game.complete_trick()
            log(f"🎯 Game {chat_id} - Trick complete")

        await process_ai_turns(game)

        return {'success': True}

    except HTTPException:
        raise
    except Exception as e:
        log(f"❌ Error in play_card: {e}")
        raise HTTPException(500, str(e))


# ============ TELEGRAM WEBHOOK ============

@app.post("/api/webhook")
async def telegram_webhook(update: dict):
    """Handle Telegram updates"""
    try:
        if 'message' in update:
            msg = update['message']
            chat_id = str(msg['chat']['id'])
            text = msg.get('text', '')

            if text == '/start':
                # Create new game
                game = Game(id=chat_id)
                games[chat_id] = game

                log(f"🎮 Game started in chat {chat_id}")

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
                    log(f"⏹️ Game {chat_id} stopped")

        elif 'callback_query' in update:
            query = update['callback_query']
            chat_id = str(query['message']['chat']['id'])
            user = query['from']
            action = query['data']

            log(f"👤 {user['first_name']} pressed {action}")

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

            await bot.answer_callback_query(query['id'])

    except Exception as e:
        log(f"❌ Error in webhook: {e}")
        import traceback
        traceback.print_exc()

    return {'ok': True}


# ============ HELPERS ============

async def start_game(game: Game):
    """Start game once 4 players joined"""
    game.start()

    log(f"🃏 Game {game.id} - 4 players ready, dealing cards")

    # Send Mini App button to chat
    mini_app_url = os.environ.get('MINI_APP_URL', 'http://localhost:5173')

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🎮 Open Game",
            web_app=WebAppInfo(url=f"{mini_app_url}?chat_id={game.id}")
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
            try:
                await bot.send_message(
                    chat_id=player.id,
                    text=f"Game started! Your hand:\n{format_hand(player.hand)}"
                )
            except Exception as e:
                log(f"⚠️ Could not DM {player.name}: {e}")

    # Process AI turns if AI starts
    await process_ai_turns(game)


async def process_ai_turns(game: Game):
    """Process all consecutive AI turns"""
    max_iterations = 100  # Prevent infinite loops
    iterations = 0

    while game.activePlayer and game.activePlayer.isAI and game.phase not in [0, 4] and iterations < max_iterations:
        iterations += 1
        await asyncio.sleep(0.5)  # Small delay for realism

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
    for suit in 'SHDC':  # Standard display order
        if suit in grouped:
            cards = ' '.join(grouped[suit]).replace('T', '10')
            lines.append(f"{suits[suit]} {cards}")

    return '\n'.join(lines)


# ============ HEALTH CHECK ============

@app.get("/health")
async def health():
    return {"status": "ok", "games": len(games)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
