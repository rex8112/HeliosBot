const { Collection } = require('discord.js');
const { Casino: CasinoDB, Table: TableDB } = require('../../tools/database');
const { Player } = require('./player');
const { Table } = require('./table');

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

    async load(data = null) {
        // Load casino from database
        if (!data) {
            data = await CasinoDB.findOne({ where: { guildId: this.id } });
        }
        if (data) {
            this.players = await Player.fromCasino(this);

            for (const c of data.channels) {
                const cc = CasinoChannel.fromJSON(this, c);
                if (cc) {
                    this.channels.set(cc.id, cc);
                }
            }
        } else {
            // Create new casino
            await this.save();
        }
        return this;
    }

    async save() {
        // Save casino to database
        await CasinoDB.upsert(this.toJSON(), { where: { guildId: this.id } });
    }

    async refreshChannels() {
        for (const c of this.channels.values()) {
            await c.refresh();
        }
    }

    toJSON() {
        return {
            guildId: this.id,
            channels: this.channels,
        };
    }

    handleInteraction(interaction) {
        // TODO: Handle interaction
    }

    // Add a new channel to the casino
    addChannel(channel) {
        if (this.channels.has(channel.id)) return this.channels.get(channel.id);
        const cc = new CasinoChannel(this, channel);
        this.channels.set(cc.id, cc);
        cc.refresh();
        this.save();
        return cc;
    }

    // Remove a channel from the casino
    removeChannel(channel) {
        this.channels.delete(channel.id);
    }

    // Get a table with the message
    getTable(message) {
        return this.Tables.get(message?.id ?? message);
    }

    getPlayer(user) {
        return this.players.get(user?.id ?? user);
    }
}

class CasinoChannel {
    constructor(casino, channel) {
        this.casino = casino;
        this.channel = channel;
        this.id = channel.id;
        this.tables = new Collection();
    }

    async refresh() {
        for (const [id, table] of this.tables.entries()) {
            const newId = await table.refresh();
            this.tables.delete(id);
            this.tables.set(newId, table);
        }
    }

    static async fromJSON(casino, data) {
        const channel = await casino.server.guild.channels.fetch(data.id);
        if (channel) {
            const cc = new CasinoChannel(casino, channel);
            for (let d of data.tables) {
                d = await TableDB.findOne({ where: { messageId: d.id } });
                const message = await this.channel.messages.fetch(d.messageId);
                const table = await new Table(casino, message).load(d);
                this.tables.set(table.id, table);
            }
            return cc;
        } else {
            return null;
        }
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