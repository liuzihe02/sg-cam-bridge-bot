import { makeBid } from '../api';

const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠', N: 'NT' };

interface BidPanelProps {
  validBids: string[];
  chatId: string;
  userId: string;
  onBid: () => void;
}

export default function BidPanel({ validBids, chatId, userId, onBid }: BidPanelProps) {
  const handleBid = async (bid: string) => {
    try {
      await makeBid(chatId, userId, bid);
      onBid();
    } catch (e) {
      // Error already shown in alert
    }
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
            {bid[0]} {SUITS[bid[1]]}
          </button>
        ))}
      </div>
    </div>
  );
}
