const { Collection } = require('discord.js');
const { Casino: CasinoDB, Table: TableDB } = require('../../tools/database');
const { Player } = require('./player');
const { Table } = require('./table');

const wait = require('util').promisify(setTimeout);

class Casino {
    constructor(server) {
        this.server = server;
        this.id = server.id;
        this.players = new Collection();
        this.channels = new Collection();
        this.changed = false;
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
                const cc = await CasinoChannel.fromJSON(this, c);
                if (cc) {
                    this.channels.set(cc.id, cc);
                }
            }
        } else {
            // Create new casino
            await this.save();
        }
        if (this.changed) {
            this.changed = false;
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

    async handleInteraction(interaction) {
        // TODO: Handle interaction
        console.log('Interaction Recieved');
        if (interaction.customId.includes('Table')) {
            const table = this.channels.get(interaction.channelId).tables.get(interaction.message.id);
            if (table) {
                await table.handleInteraction(interaction);
            }
        }
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
        const tmp = new Collection(this.tables);
        for (const [id, table] of tmp.entries()) {
            const newId = await table.refresh();
            this.tables.delete(id);
            this.tables.set(newId, table);
            await wait(2000);
        }
        this.casino.save();
    }

    async createTable(tableId) {
        const table = await Table.getTable(tableId).create(this.casino, this.channel);
        this.tables.set(table.id, table);
        this.casino.save();
        return table;
    }

    static async fromJSON(casino, data) {
        const channel = await casino.server.guild.channels.fetch(data.id);
        if (channel) {
            const cc = new CasinoChannel(casino, channel);
            for (let d of data.tables) {
                d = await TableDB.findOne({ where: { messageId: d } });
                if (d === null) {
                    casino.changed = true;
                    continue;
                }
                let message;
                try {
                    message = await cc.channel.messages.fetch(d.messageId);
                } catch (e) {
                    d.destroy();
                    casino.changed = true;
                    continue;
                }
                const table = await new Table(casino, message).load(d);
                cc.tables.set(table.id, table);
            }
            return cc;
        } else {
            return null;
        }
    }

    toJSON() {
        return {
            id: this.id,
            tables: this.tables.mapValues(t => t.id),
        };
    }
}

module.exports = {
    Casino,
};