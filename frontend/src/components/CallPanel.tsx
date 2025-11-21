import { callPartner } from '../api';

const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠' };
const VALUES = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

interface CallPanelProps {
  chatId: string;
  userId: string;
  onCall: () => void;
}

export default function CallPanel({ chatId, userId, onCall }: CallPanelProps) {
  const handleCall = async (card: string) => {
    try {
      await callPartner(chatId, userId, card);
      onCall();
    } catch (e) {
      // Error already shown in alert
    }
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
