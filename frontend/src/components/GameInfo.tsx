import { GameState } from '../types';

const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠' };

export default function GameInfo({ game }: { game: GameState }) {
  return (
    <div className="game-info">
      <div>Trump: {game.trump ? SUITS[game.trump] : 'NT'}</div>
      <div>Contract: {game.contract}</div>
      {game.declarer && <div>Declarer: {game.declarer.name}</div>}
      {game.partnerCard && <div>Partner: {translateCard(game.partnerCard)}</div>}
      {game.bid && game.bid !== 'PASS' && <div>Current Bid: {formatBid(game.bid)}</div>}
    </div>
  );
}

function translateCard(card: string): string {
  const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠' };
  return card[1].replace('T', '10') + SUITS[card[0]];
}

function formatBid(bid: string): string {
  const SUITS: Record<string, string> = { C: '♣', D: '♦', H: '♥', S: '♠', N: 'NT' };
  return bid[0] + SUITS[bid[1]];
}
