const { Collection, MessageEmbed, MessageActionRow, MessageButton } = require('discord.js');
const { Casino: CasinoDB, Table: TableDB } = require('../../tools/database');
const { Player } = require('./player');
const { Table } = require('./table');
const { BlackjackTable } = require('./blackjack');
const { COLOR } = require('../colors');
const { time } = require('@discordjs/builders');
// const { moment } = require('MomentJS');

const wait = require('util').promisify(setTimeout);

class Casino {
    constructor(server) {
        this.server = server;
        this.id = server.id;
        this.players = new Collection();
        this.channels = new Collection();
        this.changed = false;
        this.startingBalance = 10000;
        this.dailyBalance = 2000;
        this.dailyId = 1;
    }

    static TABLES = {
        Blackjack: BlackjackTable,
        Invalid: Table,
    }

    // Get all tables in the casino
    get Tables() {
        let tables = new Collection();
        for (const cc of this.channels.values()) {
            tables = tables.concat(cc.tables);
        }
        return tables;
    }

    get daysSinceStart() {
        const start = new Date(2021, 0, 1, 0);
        const now = new Date();
        return Math.floor(new Date(now - start).getTime() / (1000 * 60 * 60 * 24));
    }

    get msToMidnight() {
        return new Date(new Date().setHours(25, 0, 0, 0) - new Date()).getTime();
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
        this.changeDaily();
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
            dailyId: this.dailyId,
        };
    }

    async handleInteraction(interaction) {
        // TODO: Handle interaction
        if (interaction.customId.includes('Table')) {
            const table = this.channels.get(interaction.channelId).tables.get(interaction.message.id);
            const player = this.players.get(interaction.member.id);
            if (table && player) {
                await table.handleInteraction(interaction);
            } else {
                await interaction.reply({ content: 'Either I do not know who your are or the table you clicked. Make sure to hit New Player if you have not.', ephemeral: true });
            }
        } else if (interaction.customId === 'casinoDaily') {
            // Implement daily
            const player = this.players.get(interaction.member.id);
            if (player) {
                if (player.dailyId !== this.dailyId) {
                    player.dailyId = this.dailyId;
                    player.pay(this.dailyBalance);
                    await interaction.reply({ content: `You have recieved **${this.dailyBalance}** coins.`, ephemeral: true });
                } else {
                    await interaction.reply({ content: `You already claimed your daily check back ${time(new Date().setHours(25, 0, 0, 0) / 1000, 'R')}.`, ephemeral: true });
                }
            }
        } else if (interaction.customId === 'casinoNewPlayer') {
            // Implement new player
            if (this.players.has(interaction.member.id)) {
                await interaction.reply({ content: 'You are already in the casino.', ephemeral: true });
            } else {
                const player = await this.createPlayer(interaction.member);
                await interaction.reply({ content: `Welcome to the casino, **${player.member.displayName}**!`, ephemeral: true });
            }
        } else if (interaction.customId === 'casinoBalance') {
            // Implement balance
            const player = this.players.get(interaction.member.id);
            if (player) {
                await interaction.reply({ content: `You have **${player.balance}** coins.`, ephemeral: true });
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

    async createPlayer(member) {
        const player = new Player(this, member);
        player.pay(this.startingBalance, false);
        await player.save();
        this.players.set(player.id, player);
        return player;
    }

    changeDaily() {
        this.dailyId = this.daysSinceStart;
        this.save();
        const msToMidnight = new Date(new Date().setHours(25, 0, 0, 0) - new Date()).getTime();
        setTimeout(this.changeDaily.bind(this),
            msToMidnight);
        return this.dailyId;
    }
}

class CasinoChannel {
    constructor(casino, channel) {
        this.casino = casino;
        this.channel = channel;
        this.id = channel.id;
        this.tables = new Collection();
        this.message = null;
    }

    getEmbeds() {
        const embed = new MessageEmbed()
            .setColor(COLOR.points)
            .setTitle(`Welcome to the ${this.casino.server.guild.name} Casino`)
            .setDescription(`This casino has **${this.casino.Tables.size}** active tables, ` +
                `**${this.tables.size}** of which are found in this channel. If you have never played ` +
                'before you can start by hitting **New Player** down below. Be sure to check in daily for free points!');
        return [embed];
    }

    getComponents() {
        const components = [];
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('casinoDaily')
                    .setLabel('Daily')
                    .setStyle('SUCCESS'),
                new MessageButton()
                    .setCustomId('casinoBalance')
                    .setLabel('Balance')
                    .setStyle('SUCCESS'),
                new MessageButton()
                    .setCustomId('casinoNewPlayer')
                    .setLabel('New Player')
                    .setStyle('PRIMARY'),
            );
        const row2 = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('casinoSettings')
                    .setLabel('Settings')
                    .setStyle('SECONDARY')
                    .setDisabled(true),
            );
        components.push(row, row2);
        return components;
    }

    async refresh() {
        const tmp = new Collection(this.tables);
        for (const [id, table] of tmp.entries()) {
            const newId = await table.refresh();
            this.tables.delete(id);
            this.tables.set(newId, table);
            await wait(2000);
        }
        await this.refreshCasinoMessage();
        this.casino.save();
    }

    async refreshCasinoMessage() {
        if (this.message) {
            await this.message.delete();
        }
        this.message = await this.channel.send({ embeds: this.getEmbeds(), components: this.getComponents() });
    }

    async createTable(tableId, settings = {}) {
        const table = await Casino.TABLES[tableId].createTable(this.casino, this.channel, settings);
        this.tables.set(table.id, table);
        await this.refreshCasinoMessage();
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
                    casino.changed = true;
                    continue;
                }
                const tableClass = Casino.TABLES[d.gameId];
                const table = await new tableClass(casino, message).load(d);
                cc.tables.set(table.id, table);
                await wait(1010);
            }
            if (data.messageId) {
                try {
                    cc.message = await cc.channel.messages.fetch(data.messageId);
                } catch (e) {
                    casino.changed = true;
                }
            } else {
                this.message = null;
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
            messageId: this.message?.id ?? null,
        };
    }
}

module.exports = {
    Casino,
};