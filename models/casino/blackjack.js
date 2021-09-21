const { Table } = require('./table');

class BlackjackTable extends Table {
    constructor(casino, message) {
        super(casino, message);

        this.gameId = 'Blackjack';
        this.name = 'Blackjack Table';
        this.description = 'The goal of the game is to get as close to 21 as possible without going over. ' +
        'Beat the dealer to win. Ties pay back 1:1.\n\n';
    }

    handleInteraction(interaction) {
        // TODO: Implement
        super.handleInteraction(interaction);
    }
}

Table.TABLES.set(BlackjackTable.gameId, BlackjackTable);