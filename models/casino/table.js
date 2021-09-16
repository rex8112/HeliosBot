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
        this.deck = new Deck();

        this.minBet = 0;
        this.maxBet = 0;
        this.maxPlayers = 0;
        this.minPlayers = 0;
    }

    get joinable() { return this.state === Table.STATES.Lobby && this.players.size < this.maxPlayers; }

    static STATES = {
        Unloaded: 'unloaded',
        Paused: 'paused',
        Inactive: 'inactive',
        Lobby: 'lobby',
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
            for (const player in data.players) {
                const p = this.casino.getPlayer(player);
                if (this.players.includes(p)) continue;
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
            players:this.players,
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

    getLobbyEmbeds() {
        const playerString = this.players.map(p => userMention(p.id)).join('\n');
        const embed = new MessageEmbed()
            .setColor(COLOR.creation)
            .setTitle(`Lobby for ${this.name}`)
            .setDescription(this.description)
            .setFooter(`Table ID: ${this.id}`)
            .addField('Players', playerString ? playerString : 'None', true)
            .addField('Technical Info', `Max Players: **${this.maxPlayers}**\nMinimum Players: **${this.minPlayers}**` +
            `\n\nMaximum Bet: **${this.maxBet}**\nMinimum Bet: **${this.minBet}**`, true);
        return [embed];
    }

    getLobbyComponents() {
        const components = [];
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('casinoTableJoin')
                    .setLabel('Join')
                    .setStyle('PRIMARY')
                    .setDisabled(!this.joinable),
                new MessageButton()
                    .setCustomId('casinoTableLeave')
                    .setLabel('Leave')
                    .setStyle('SECONDARY'),
            );
        components.push(row);
        return components;
    }

    async handleInteraction(interaction) {
        console.log(`${this.id} Recieved Interaction`);
    }

    async updateMessage() {
        const embeds = this.getLobbyEmbeds();
        const components = this.getLobbyComponents();
        const message = this.message;
        await message.edit({ content: null, embeds, components });
    }
}

module.exports = {
    Table,
};