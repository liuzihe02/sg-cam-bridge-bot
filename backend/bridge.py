import random
from typing import List, Optional, Set
from dataclasses import dataclass, field

SUITS = ['C', 'D', 'H', 'S']  # Clubs, Diamonds, Hearts, Spades
VALUES = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
SUIT_ORDER = {'C': 0, 'D': 1, 'H': 2, 'S': 3, 'N': 4}  # N = No Trump
VALUE_ORDER = {v: i for i, v in enumerate(VALUES)}


def create_deck() -> List[str]:
    """Create a standard 52-card deck"""
    return [s + v for s in SUITS for v in VALUES]


def calculate_points(hand: List[str]) -> int:
    """Calculate hand points: A=4, K=3, Q=2, J=1, +1 per card after 4th in suit"""
    points = 0
    for card in hand:
        value = card[1]
        if value == 'A':
            points += 4
        elif value == 'K':
            points += 3
        elif value == 'Q':
            points += 2
        elif value == 'J':
            points += 1

    # Distribution points
    suit_counts = {'C': 0, 'D': 0, 'H': 0, 'S': 0}
    for card in hand:
        suit_counts[card[0]] += 1

    for count in suit_counts.values():
        if count > 4:
            points += (count - 4)

    return points


@dataclass
class Player:
    id: str
    name: str
    hand: List[str] = field(default_factory=list)
    isAI: bool = False
    tricks: int = 0
    game: Optional['Game'] = None

    def valid_cards(self) -> List[str]:
        """Return list of playable cards"""
        if not self.game or self.game.phase != 3:  # Not PLAY phase
            return []

        game = self.game
        hand = self.hand

        # Leading a trick
        if not game.currentTrick[0]:
            result = hand.copy()
            # Can't lead trump unless broken or only have trump
            if game.trump and not game.trumpBroken:
                non_trump = [c for c in hand if c[0] != game.trump]
                if non_trump:
                    result = non_trump
            return result

        # Following a trick
        lead_suit = game.currentTrick[0][0]
        same_suit = [c for c in hand if c[0] == lead_suit]
        return same_suit if same_suit else hand

    def make_bid(self, bid: Optional[str] = None):
        """Make a bid (human provides bid, AI auto-generates)"""
        if self.isAI:
            bid = self._ai_bid()

        if not bid:
            return

        self.game.process_bid(self, bid)

    def call_partner(self, card: Optional[str] = None):
        """Call partner card (human provides card, AI auto-generates)"""
        if self.isAI:
            card = self._ai_call_partner()

        if not card:
            return

        self.game.process_call(self, card)

    def play_card(self, card: Optional[str] = None):
        """Play a card (human provides card, AI auto-generates)"""
        if self.isAI:
            valid = self.valid_cards()
            card = random.choice(valid) if valid else None

        if not card or card not in self.hand:
            return

        self.game.process_play(self, card)

    def _ai_bid(self) -> str:
        """Simple AI bidding logic"""
        points = calculate_points(self.hand)
        valid_bids = list(self.game.valid_bids())

        # Weak hand: pass
        if points < 10:
            return 'PASS'

        # Strong hand: bid
        non_pass = [b for b in valid_bids if b != 'PASS']
        if non_pass:
            # Pick a random valid bid (simple AI)
            return random.choice(non_pass[:3]) if len(non_pass) > 3 else random.choice(non_pass)

        return 'PASS'

    def _ai_call_partner(self) -> str:
        """AI picks a partner card (random high card not in hand)"""
        deck = create_deck()
        available = [c for c in deck if c not in self.hand]
        # Prefer high cards
        for value in ['A', 'K', 'Q', 'J']:
            high_cards = [c for c in available if c[1] == value]
            if high_cards:
                return random.choice(high_cards)
        return random.choice(available) if available else 'SA'


@dataclass
class Game:
    id: str
    players: List[Player] = field(default_factory=list)
    phase: int = 0  # 0=JOIN, 1=BID, 2=CALL, 3=PLAY, 4=END
    activePlayer: Optional[Player] = None

    # Bidding
    bid: str = 'PASS'
    bidder: Optional[Player] = None
    passes: int = 0
    last_bidder_index: int = -1

    # Partner
    partnerCard: Optional[str] = None
    partner: Optional[Player] = None

    # Playing
    trump: str = ''
    contract: int = 7
    currentTrick: List[Optional[str]] = field(default_factory=lambda: [None, None, None, None])
    trumpBroken: bool = False
    currentSuit: Optional[str] = None
    trickLeader: int = 0

    # Tracking
    sets: List[int] = field(default_factory=lambda: [0, 0, 0, 0])

    def add_human(self, user_id: str, name: str) -> bool:
        """Add human player"""
        if len(self.players) >= 4:
            return False
        if any(p.id == user_id for p in self.players):
            return False

        player = Player(id=user_id, name=name, game=self)
        self.players.append(player)
        return True

    def add_AI(self) -> bool:
        """Add AI player"""
        if len(self.players) >= 4:
            return False

        ai_num = sum(1 for p in self.players if p.isAI) + 1
        player = Player(
            id=f"AI_{ai_num}",
            name=f"AI Player {ai_num}",
            isAI=True,
            game=self
        )
        self.players.append(player)
        return True

    def full(self) -> bool:
        """Check if game has 4 players"""
        return len(self.players) == 4

    def start(self):
        """Start the game - deal cards and begin bidding"""
        if not self.full():
            return

        # Deal cards
        deck = create_deck()
        random.shuffle(deck)

        # Check for wash (any player with <4 points)
        max_attempts = 10
        for _ in range(max_attempts):
            random.shuffle(deck)
            hands = [deck[i*13:(i+1)*13] for i in range(4)]

            if all(calculate_points(hand) >= 4 for hand in hands):
                break

        # Assign hands
        for i, player in enumerate(self.players):
            player.hand = sorted(hands[i], key=lambda c: (SUITS.index(c[0]), VALUES.index(c[1])))
            player.tricks = 0

        # Start bidding
        self.phase = 1
        self.activePlayer = self.players[0]
        self.passes = 0
        self.last_bidder_index = -1

    def valid_bids(self) -> Set[str]:
        """Return set of valid bids"""
        bids = {'PASS'}

        if self.bid == 'PASS':
            # First bid can be anything
            for level in range(1, 8):
                for suit in ['C', 'D', 'H', 'S', 'N']:
                    bids.add(f"{level}{suit}")
        else:
            # Must bid higher
            current_level = int(self.bid[0])
            current_suit = self.bid[1]
            current_order = SUIT_ORDER[current_suit]

            for level in range(current_level, 8):
                for suit in ['C', 'D', 'H', 'S', 'N']:
                    bid_str = f"{level}{suit}"
                    if level > current_level or (level == current_level and SUIT_ORDER[suit] > current_order):
                        bids.add(bid_str)

        return bids

    def process_bid(self, player: Player, bid: str):
        """Process a player's bid"""
        if self.phase != 1 or player != self.activePlayer:
            return

        if bid not in self.valid_bids():
            return

        player_index = self.players.index(player)

        if bid == 'PASS':
            self.passes += 1
        else:
            self.bid = bid
            self.bidder = player
            self.passes = 0
            self.last_bidder_index = player_index

        # Check if bidding is over (3 consecutive passes after a bid)
        if self.passes >= 3 and self.last_bidder_index >= 0:
            # Move to CALL phase
            self.phase = 2
            self.activePlayer = self.bidder

            # Set trump and contract
            level = int(self.bid[0])
            suit = self.bid[1]
            self.contract = 6 + level
            self.trump = '' if suit == 'N' else suit
        else:
            # Next player
            next_index = (player_index + 1) % 4
            self.activePlayer = self.players[next_index]

    def process_call(self, player: Player, card: str):
        """Process partner selection"""
        if self.phase != 2 or player != self.activePlayer:
            return

        self.partnerCard = card

        # Check if declarer called their own card (playing alone)
        if card in player.hand:
            self.partner = player

        # Move to PLAY phase
        self.phase = 3

        # Determine who leads
        declarer_index = self.players.index(self.bidder)
        if self.trump:  # Trump contract
            lead_index = (declarer_index + 1) % 4
        else:  # No Trump
            lead_index = declarer_index

        self.trickLeader = lead_index
        self.activePlayer = self.players[lead_index]
        self.currentTrick = [None, None, None, None]

    def process_play(self, player: Player, card: str):
        """Process a card play"""
        if self.phase != 3 or player != self.activePlayer:
            return

        if card not in player.valid_cards():
            return

        # Remove card from hand
        player.hand.remove(card)

        # Add to current trick
        player_index = self.players.index(player)
        self.currentTrick[player_index] = card

        # Check if this reveals partner
        if card == self.partnerCard and not self.partner:
            self.partner = player

        # Set current suit if leading
        if not self.currentSuit:
            self.currentSuit = card[0]

        # Check if trump was broken
        if self.trump and card[0] == self.trump and self.currentSuit != self.trump:
            self.trumpBroken = True

        # Check if trick is complete
        if all(self.currentTrick):
            # Don't advance to next player yet
            return

        # Next player
        next_index = (player_index + 1) % 4
        self.activePlayer = self.players[next_index]

    def complete_trick(self):
        """Resolve the current trick and move to next"""
        if not all(self.currentTrick):
            return

        # Determine winner
        winner_index = self._trick_winner()
        self.players[winner_index].tricks += 1
        self.sets[winner_index] += 1

        # Check if game is over
        if all(len(p.hand) == 0 for p in self.players):
            self.phase = 4
            self.activePlayer = None
            return

        # Next trick
        self.currentTrick = [None, None, None, None]
        self.currentSuit = None
        self.trickLeader = winner_index
        self.activePlayer = self.players[winner_index]

    def _trick_winner(self) -> int:
        """Determine winner of current trick"""
        lead_suit = self.currentTrick[self.trickLeader][0]

        best_index = self.trickLeader
        best_card = self.currentTrick[self.trickLeader]

        for i in range(4):
            if i == self.trickLeader:
                continue

            card = self.currentTrick[i]
            card_suit = card[0]

            # Trump beats non-trump
            if self.trump:
                if card_suit == self.trump and best_card[0] != self.trump:
                    best_index = i
                    best_card = card
                    continue

                if card_suit == self.trump and best_card[0] == self.trump:
                    if VALUE_ORDER[card[1]] < VALUE_ORDER[best_card[1]]:
                        best_index = i
                        best_card = card
                    continue

            # Following suit
            if card_suit == lead_suit and best_card[0] == lead_suit:
                if VALUE_ORDER[card[1]] < VALUE_ORDER[best_card[1]]:
                    best_index = i
                    best_card = card

        return best_index

    @property
    def declarer(self) -> Optional[Player]:
        """Get declarer (bidder)"""
        return self.bidder
