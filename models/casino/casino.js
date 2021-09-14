const { Collection } = require('discord.js');

class Casino {
    constructor(server) {
        this.server = server;
        this.id = server.id;
        this.players = new Collection();
        this.channels = new Collection();
    }

    // Get all tables in the casino
    get Tables() {
        let tables = new Collection();
        for (const cc of this.channels.values()) {
            tables = tables.concat(cc.tables);
        }
        return tables;
    }

    async load() {
        // TODO: Load casino from database
        return this;
    }

    async save() {
        // TODO: Save casino to database
    }

    toJSON() {
        return {
            guildId: this.id,
            players: this.players,
            channels: this.channels,
        };
    }

    handleInteraction(interaction) {
        // TODO: Handle interaction
    }

    // Add a new channel to the casino
    addChannel(channel) {
        const cc = new CasinoChannel(this, channel);
        this.channels.set(cc.id, cc);
    }

    // Remove a channel from the casino
    removeChannel(channel) {
        this.channels.delete(channel.id);
    }

    // Get a table with the message
    getTable(message) {
        return this.Tables.find(t => t.id === message.id);
    }
}

class CasinoChannel {
    constructor(casino, channel) {
        this.casino = casino;
        this.channel = channel;
        this.id = channel.id;
        this.tables = new Collection();
    }

    toJSON() {
        return {
            id: this.id,
            tables: this.tables,
        };
    }
}

module.exports = {
    Casino,
};