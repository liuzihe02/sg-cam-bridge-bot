import { playCard } from '../api';

const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠' };

interface HandProps {
  cards: string[];
  validCards: string[];
  disabled: boolean;
  chatId: string;
  userId: string;
  onPlay: () => void;
}

export default function Hand({ cards, validCards, disabled, chatId, userId, onPlay }: HandProps) {
  const grouped: Record<string, string[]> = {};
  cards.forEach(card => {
    const suit = card[0];
    if (!grouped[suit]) grouped[suit] = [];
    grouped[suit].push(card);
  });

  const handlePlay = async (card: string) => {
    if (disabled || !validCards.includes(card)) return;
    try {
      await playCard(chatId, userId, card);
      onPlay();
    } catch (e) {
      // Error already shown in alert
    }
  };

  return (
    <div className="hand">
      {['S', 'H', 'D', 'C'].map(suit => {
        if (!grouped[suit]) return null;
        return (
          <div key={suit} className="suit-row">
            <span className="suit-icon">{SUITS[suit]}</span>
            <div className="cards">
              {grouped[suit].map(card => (
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
        );
      })}
    </div>
  );
}
