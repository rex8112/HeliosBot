const { Table } = require('./table');
const { Hand } = require('../playingCards');

class BlackjackTable extends Table {
    constructor(casino, message) {
        super(casino, message);

        this.gameId = 'Blackjack';
        this.name = 'Blackjack Table';
        this.description = 'The goal of the game is to get as close to 21 as possible without going over. ' +
        'Beat the dealer to win. Ties pay back 1:1.\n\n';

        this.dealer = new Hand();
    }

    async startPlaying() {
        this.deck.reset();
        this.deck.clearHands();
        for (const player of this.players.values()) {
            this.deck.addHand(player.hand);
        }
        this.deck.addHand(this.dealer);
        this.deck.shuffle();
        this.deck.deal(2);
        await super.startPlaying();
    }

    hit(member) {
        const player = this.players.get(member.id);
        player.hand.add(this.deck.draw());
    }

    handleInteraction(interaction) {
        // TODO: Implement
        super.handleInteraction(interaction);
    }
}

Table.TABLES.set(BlackjackTable.gameId, BlackjackTable);