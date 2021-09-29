const Suits = {
    Hearts: 'hearts',
    Diamonds: 'diamonds',
    Spades: 'spades',
    Clubs: 'clubs',
};

class Card {
    constructor(suit, rank, aceHigh = true) {
        this._suit = suit;
        this.rank = rank;
        this.aceHigh = aceHigh;
    }

    static Suits = [Suits.Hearts, Suits.Diamonds, Suits.Spades, Suits.Clubs];
    static Ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

    get suitIcon() {
        switch (this._suit) {
        case Suits.Hearts:
            return '♥';
        case Suits.Diamonds:
            return '♦';
        case Suits.Spades:
            return '♠';
        case Suits.Clubs:
            return '♣';
        default:
            return '?';
        }
    }

    get suit() {
        return this._suit;
    }

    _getValue() {
        switch (this.rank) {
        case 'A':
            return this.aceHigh ? 14 : 1;
        case 'J':
            return 11;
        case 'Q':
            return 12;
        case 'K':
            return 13;
        default:
            return parseInt(this.rank, 10);
        }
    }

    compareToCard(card) {
        return this._getValue() - card._getValue();
    }

    toString() {
        return `${this.rank} of ${this.suit}`;
    }

    toShortString() {
        return `${this.rank}${this.suitIcon}`;
    }

    toJSON() {
        return `${this.rank}${this.suit[0]}`;
    }

    static fromJSON(json) {
        const card = new Card();
        card.rank = json[0];
        card.suit = Card.Suits.find(suit => suit.startsWith(json[1]));
        return card;
    }
}

class Deck {
    constructor(aceHigh = true) {
        this.deck = [];
        this.discardPile = [];
        this.hands = [];
        this.aceHigh = aceHigh;
        this.reset();
    }

    reset() {
        this.deck = [];
        const suits = Card.Suits;
        const ranks = Card.Ranks;
        for (const suit of suits) {
            for (const rank of ranks) {
                this.deck.push(new Card(suit, rank, this.aceHigh));
            }
        }
        for (const hand of this.hands) {
            hand.clear();
        }
    }

    shuffle() {
        const deck = this.deck = this.deck.concat(this.discardPile);
        this.discardPile = [];
        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }
    }

    draw(numCards = 1) {
        const cards = [];
        for (let i = 0; i < numCards; i++) {
            cards.push(this.deck.pop());
        }
        return cards.length > 1 ? cards : cards[0];
    }

    deal(numCards) {
        for (let i = 0; i < numCards; i++) {
            for (const hand of this.hands) {
                hand.add(this.draw());
            }
        }
    }

    discard(card) {
        this.discardPile.push(card);
    }

    addHand(hand) {
        this.hands.push(hand);
    }

    clearHands() {
        this.hands = [];
    }
}

class Hand {
    constructor() {
        this.cards = [];
    }

    add(card) {
        this.cards.push(card);
    }

    addMany(cards) {
        this.cards.push(...cards);
    }

    toString() {
        return this.cards.join(', ');
    }

    toShortString() {
        return this.cards.map(card => card.toShortString()).join(', ');
    }

    toJSON() {
        return this.cards.map(card => card.toJSON());
    }

    static fromJSON(json) {
        const hand = new Hand();
        for (const card of json) {
            hand.add(Card.fromJSON(card));
        }
        return hand;
    }

    clear() {
        this.cards = [];
    }
}

class HandFinders {
    /**
     * @param {Card[]} cards
     * @param {string} rank
     * @returns {Card[]} the cards with the given rank
     */
    static getRank(cards, rank) {
        return cards.filter(card => card.rank === rank);
    }

    /**
     * @param {Card[]} cards
     * @param {string} suit
     * @returns {Card[]} the cards with the given suit
     */
    static getSuit(cards, suit) {
        return cards.filter(card => card._suit === suit);
    }

    static getSuitCount(cards, suit) {
        return HandFinders.getSuit(cards, suit).length;
    }

    static getRankCount(cards, rank) {
        return HandFinders.getRank(cards, rank).length;
    }

    /**
     * @param {Card[]} cards
     * @returns {Card} the highest card in the hand
     */
    static getHighCard(cards) {
        return cards.sort((a, b) => b.rank - a.rank)[0];
    }

    static getPairs(cards) {
        const ranks = Card.Ranks;
        const pairs = [];
        for (const rank of ranks) {
            const c = HandFinders.getRank(cards, rank);
            if (c.length >= 2) {
                pairs.push([c[0], c[1]]);
            }
        }
        return pairs;
    }

    static getThreeOfAKinds(cards) {
        const ranks = Card.Ranks;
        const threeOfAKinds = [];
        for (const rank of ranks) {
            const c = HandFinders.getRank(cards, rank);
            if (c.length >= 3) {
                threeOfAKinds.push([c[0], c[1], c[2]]);
            }
        }
        return threeOfAKinds;
    }

    static getFourOfAKinds(cards) {
        const ranks = Card.Ranks;
        const fourOfAKinds = [];
        for (const rank of ranks) {
            const c = HandFinders.getRank(cards, rank);
            if (c.length >= 4) {
                fourOfAKinds.push([c[0], c[1], c[2], c[3]]);
            }
        }
        return fourOfAKinds;
    }

    static getFullHouse(cards) {
        const pairs = HandFinders.getPairs(cards);
        const threeOfAKinds = HandFinders.getThreeOfAKinds(cards);
        if (pairs.length >= 2 && threeOfAKinds.length >= 1) {
            for (const threeOfAKind of threeOfAKinds) {
                const unequalPair = pairs.find(pair => pair[0].rank !== threeOfAKind[0].rank);
                if (unequalPair) {
                    return threeOfAKind.concat(unequalPair);
                }
            }
        }
        return [];
    }

    static getFlush(cards) {
        const suits = Card.Suits;
        const flush = [];
        for (const suit of suits) {
            const c = HandFinders.getSuit(cards, suit);
            if (c.length >= 5) {
                return c.slice(0, 5);
            }
        }
        return flush;
    }

    static getStraight(cards) {
        const ranks = Card.Ranks.slice(0, Card.Ranks.length - 4);
        for (let i = 0; i < ranks.length; i++) {
            const c0 = HandFinders.getRank(cards, Card.Ranks[i])[0];
            const c1 = HandFinders.getRank(cards, Card.Ranks[i + 1])[0];
            const c2 = HandFinders.getRank(cards, Card.Ranks[i + 2])[0];
            const c3 = HandFinders.getRank(cards, Card.Ranks[i + 3])[0];
            const c4 = HandFinders.getRank(cards, Card.Ranks[i + 4])[0];
            if (c0 && c1 && c2 && c3 && c4) {
                return [c0, c1, c2, c3, c4];
            }
        }
        return [];
    }

    static getStraightFlush(cards) {
        const flush = HandFinders.getFlush(cards);
        if (flush.length >= 5) {
            const straight = HandFinders.getStraight(flush);
            if (straight.length >= 5) {
                return straight;
            }
        }
        return [];
    }

    static getRoyalFlush(cards) {
        const flush = HandFinders.getFlush(cards);
        if (flush.length >= 5) {
            const straight = HandFinders.getStraight(flush);
            if (straight.length >= 5) {
                const c = HandFinders.getRank(straight, 'A');
                if (c.length >= 1) {
                    return straight;
                }
            }
        }
        return [];
    }

    static getBlackJackValue(card) {
        if (card.rank === 'A') {
            return 11;
        }
        if (card.rank === 'K' || card.rank === 'Q' || card.rank === 'J') {
            return 10;
        }
        return parseInt(card.rank);
    }

    static getBlackJackScore(cards) {
        let score = 0;
        let elevens = 0;
        for (const card of cards) {
            const tmp = HandFinders.getBlackJackValue(card);
            if (tmp === 11) {
                elevens += 1;
            } else {
                score += tmp;
            }
        }
        for (let i = 0; i < elevens; i++) {
            if (score + 11 <= 21) {
                score += 11;
            } else {
                score += 1;
            }
        }
        return score;
    }

}

module.exports = {
    Card,
    Deck,
    Hand,
    HandFinders,
    Suits,
};