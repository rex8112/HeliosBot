const { Table } = require('./table');

class BlackjackTable extends Table {
    constructor(casino, message) {
        super(casino, message);
    }

    handleInteraction(interaction) {
        // TODO: Implement
        super.handleInteraction(interaction);
    }
}

Table.TABLES.set(BlackjackTable.gameId, BlackjackTable);