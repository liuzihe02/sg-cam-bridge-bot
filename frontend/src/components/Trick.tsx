import { Player } from '../types';

const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠' };

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
              {card[1].replace('T', '10')} {SUITS[card[0]]}
            </div>
          ) : (
            <div className="card-placeholder">—</div>
          )}
        </div>
      ))}
    </div>
  );
}
