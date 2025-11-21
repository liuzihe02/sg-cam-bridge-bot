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
  bid: string;
}

export interface Player {
  id: string;
  name: string;
  tricks: number;
}
