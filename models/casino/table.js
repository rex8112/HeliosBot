const { Collection, MessageEmbed, MessageActionRow, MessageButton } = require('discord.js');
const { userMention } = require('@discordjs/builders');
const { Deck } = require('../playingCards');
const { COLOR } = require('../colors');
const { Table: TableDB } = require('../../tools/database');

class Table {
    constructor(casino, message) {
        this.casino = casino;
        this.id = message.id;
        this.channel = message.channel;
        this.message = message;
        this.messages = [];

        this.gameId = 'Invalid';
        this.name = 'Invalid Table';
        this.description = 'No description. Honestly, if you are seeing this outside of a testing environment then something is very wrong. Please do not bet anything.';

        this.players = new Collection();
        this.winners = new Collection();
        this.losers = new Collection();
        this.bets = new Collection();
        this.state = Table.STATES.Unloaded;
        this.paused = false;
        this.deck = new Deck();

        this.minBet = 0;
        this.maxBet = 0;
        this.maxPlayers = 4;
        this.minPlayers = 1;
    }

    get Joinable() { return this.state === Table.STATES.Lobby && this.players.size < this.maxPlayers; }
    get Playable() { return this.state === Table.STATES.Lobby && this.players.size >= this.minPlayers; }
    get Bettable() { return this.state === Table.STATES.Betting; }

    get State() { return this.paused ? Table.STATES.Paused : this.state; }

    get ReturnRow() {
        return new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setLabel('Return')
                    .setStyle('LINK')
                    .setURL(this.message.url),
            );
    }

    static STATES = {
        Unloaded: 'unloaded',
        Paused: 'paused',
        Inactive: 'inactive',
        Lobby: 'lobby',
        Betting: 'betting',
        Setup: 'setup',
    }

    static TABLES = new Map();

    /**
     * @param {string} id
     * @returns {Table}
     * @static
     */
    static getTable(id) {
        return Table.TABLES.get(id) ?? Table;
    }

    static async create(casino, channel) {
        const message = await channel.send('Creating table...');
        const table = new Table(casino, message);
        // TEMPORARY
        table.state = Table.STATES.Lobby;
        // TEMPORARY
        await table.save();
        await table.updateMessage();
        return table;
    }

    async save(oldId = null) {
        if (oldId) {
            await TableDB.update({ messageId: this.id }, { where: { messageId: oldId } });
        }
        await TableDB.upsert(this.toJSON());
    }

    async load(data = null) {
        if (!data) {
            data = await TableDB.findOne({ where: { messageId: this.id } });
        }
        if (data) {
            if (data.gameId != this.gameId) return this;
            // Get messages
            this.message = await this.channel.messages.fetch(data.messageId);
            for (const message in data.messages) {
                const m = await this.channel.messages.fetch(message);
                if (this.messages.includes(m)) continue;
                this.messages.push(m);
            }
            // Get players
            for (const player of data.players) {
                const p = this.casino.getPlayer(player);
                if (!p || this.players.has(p.id)) continue;
                this.players.set(p.id, p);
            }
            // Get bets
            this.bets = new Collection(data.bets);
            // Get state
            this.state = data.state;
            // Get settings
            this.minBet = data.settings.minBet;
            this.maxBet = data.settings.maxBet;
            this.maxPlayers = data.settings.maxPlayers;
            this.minPlayers = data.settings.minPlayers;
        }
        return this;
    }

    async refresh() {
        const oldState = this.state;
        const oldId = this.id;
        this.state = Table.STATES.Paused;
        await this.message.delete('Refreshing Table');
        this.message = await this.channel.send('Refreshing Table...');
        this.id = this.message.id;
        this.state = oldState;
        await this.updateMessage();
        this.save(oldId);
        return this.id;
    }

    toJSON() {
        return {
            channelId: this.channel.id,
            guildId: this.casino.id,
            messageId: this.id,
            gameId: this.gameId,
            messages: this.messages.map(m => m.id),
            players:this.players.map(p => p.id),
            bets: this.bets,
            state: this.state,
            settings: {
                minBet: this.minBet,
                maxBet: this.maxBet,
                maxPlayers: this.maxPlayers,
                minPlayers: this.minPlayers,
            },
        };
    }

    setBetLimit(min, max) {
        this.minBet = min;
        this.maxBet = max;
        return this;
    }

    setPlayerLimit(min, max) {
        this.minPlayers = min;
        this.maxPlayers = max;
        return this;
    }

    getEmbeds() {
        const playerString = this.players.map(p => userMention(p.id)).join('\n');
        const embeds = [];
        if (this.state === Table.STATES.Lobby) {
            const embed = new MessageEmbed()
                .setColor(COLOR.creation)
                .setTitle(`Lobby for ${this.name}`)
                .setDescription(this.description)
                .setFooter(`Table ID: ${this.id}`)
                .addField('Players', playerString ? playerString : 'None', true)
                .addField('Technical Info', `Max Players: **${this.maxPlayers}**\nMinimum Players: **${this.minPlayers}**` +
                `\n\nMaximum Bet: **${this.maxBet}**\nMinimum Bet: **${this.minBet}**`, true);
            embeds.push(embed);
        } else if (this.Paused) {
            const embed = new MessageEmbed()
                .setColor(COLOR.creation)
                .setTitle(`${this.name} Paused`)
                .setDescription('The game is currently paused.')
                .setFooter(`Table ID: ${this.id}`)
                .addField('Players', playerString ? playerString : 'None', true);
            embeds.push(embed);
        }
        return embeds;
    }

    getComponents() {
        const components = [];
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('casinoTableJoin')
                    .setLabel('Join')
                    .setStyle('PRIMARY')
                    .setDisabled(!this.Joinable),
                new MessageButton()
                    .setCustomId('casinoTableLeave')
                    .setLabel('Leave')
                    .setStyle('SECONDARY'),
            );
        const row2 = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('casinoTableStart')
                    .setLabel('Start')
                    .setStyle('SUCCESS')
                    .setDisabled(!this.Playable),
            );
        components.push(row);
        components.push(row2);
        return components;
    }

    scheduleRun(time) {
        this.runProcess = setTimeout(this.run, time);
    }

    stopRun() {
        clearTimeout(this.runProcess);
    }

    async run() {
        // TODO: Implement
    }

    async join(player) {
        if (this.players.has(player.id) || player.Table) return false;
        this.players.set(player.id, player);
        player.Table = this;
        await this.save();
        return true;
    }

    async leave(player) {
        if (!this.players.has(player.id)) return false;
        this.players.delete(player.id);
        player.Table = null;
        await this.save();
        return true;
    }

    async handleInteraction(interaction) {
        console.log(`${this.id} Recieved Interaction`);
        if (interaction.customId === 'casinoTableJoin') {
            const player = this.casino.getPlayer(interaction.user.id);
            if (!await this.join(player)) {
                const table = player.Table;
                if (table?.id !== this.id) {
                    await interaction.reply({ content: 'You are already in **another** table.', components: [table.ReturnRow], ephemeral: true });
                } else {
                    await interaction.reply({ content: 'You are already in this table.', components: [this.ReturnRow], ephemeral: true });
                }
            } else {
                await this.updateMessage(undefined, undefined, interaction);
            }
        } else if (interaction.customId === 'casinoTableLeave') {
            const player = this.casino.getPlayer(interaction.user.id);
            if (!await this.leave(player)) {
                await interaction.reply({ content: 'You are not in this table.', components: [this.ReturnRow], ephemeral: true });
            } else {
                await this.updateMessage(undefined, undefined, interaction);
            }
        } else if (interaction.customId === 'casinoTableStart') {
            // await this.start();
        }
    }

    async updateMessage(embeds = null, components = null, interaction = null) {
        if (!embeds) embeds = this.getEmbeds();
        if (!components) components = this.getComponents();
        const message = this.message;
        if (interaction) {
            await interaction.update({ content: null, components, embeds });
        } else {
            await message.edit({ content: null, embeds, components });
        }
    }
}

module.exports = {
    Table,
};