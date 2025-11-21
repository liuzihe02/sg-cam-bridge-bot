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
          user?: { id: number; first_name: string };
          start_param?: string;
        };
      };
    };
  }
}

export default function App() {
  const [game, setGame] = useState<GameState | null>(null);
  const [error, setError] = useState<string>('');
  const [chatId, setChatId] = useState<string>('');
  const [userId, setUserId] = useState<string>('');

  useEffect(() => {
    const tg = window.Telegram?.WebApp;

    if (tg) {
      tg.ready();
      tg.expand();

      // Get user and chat IDs from Telegram
      const user = tg.initDataUnsafe?.user;
      const uid = user ? String(user.id) : '';
      const cid = tg.initDataUnsafe?.start_param || new URLSearchParams(window.location.search).get('chat_id') || uid;

      setUserId(uid);
      setChatId(cid);

      if (!uid || !cid) {
        setError('Could not get user/chat ID from Telegram');
        return;
      }

      // Load game initially
      loadGame(cid, uid);

      // Poll every 2 seconds
      const interval = setInterval(() => {
        loadGame(cid, uid);
      }, 2000);

      return () => clearInterval(interval);
    } else {
      // Development mode - use test IDs
      const testUserId = '123456';
      const testChatId = new URLSearchParams(window.location.search).get('chat_id') || '-1001234567890';
      setUserId(testUserId);
      setChatId(testChatId);

      loadGame(testChatId, testUserId);

      const interval = setInterval(() => {
        loadGame(testChatId, testUserId);
      }, 2000);

      return () => clearInterval(interval);
    }
  }, []);

  const loadGame = async (cid: string, uid: string) => {
    try {
      const data = await getGame(cid, uid);
      setGame(data);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load game');
    }
  };

  const refresh = () => {
    if (chatId && userId) {
      loadGame(chatId, userId);
    }
  };

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!game) {
    return <div className="loading">Loading game...</div>;
  }

  const isYourTurn = game.activePlayerId === userId;

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
        <BidPanel
          validBids={game.validBids}
          chatId={chatId}
          userId={userId}
          onBid={refresh}
        />
      )}

      {game.phase === 'CALL' && isYourTurn && (
        <CallPanel
          chatId={chatId}
          userId={userId}
          onCall={refresh}
        />
      )}

      {game.phase === 'PLAY' && (
        <Hand
          cards={game.hand}
          validCards={game.validCards}
          disabled={!isYourTurn}
          chatId={chatId}
          userId={userId}
          onPlay={refresh}
        />
      )}

      {!isYourTurn && game.phase !== 'END' && game.phase !== 'JOIN' && (
        <div className="waiting">
          Waiting for {game.players.find(p => p.id === game.activePlayerId)?.name}...
        </div>
      )}

      {game.phase === 'END' && (
        <div className="game-over">
          <h2>Game Over!</h2>
          <div className="scores">
            {game.players.map(p => (
              <div key={p.id}>
                {p.name}: {p.tricks} tricks
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
