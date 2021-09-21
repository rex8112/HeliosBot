const { Collection, MessageEmbed, MessageActionRow, MessageButton, MessageSelectMenu } = require('discord.js');
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

        this.settings = {
            minBet: 100,
            maxBet: 1000,
            minPlayers: 1,
            maxPlayers: 4,
            bettingTime: 30000,
            lobbyTime: 30000,
        };

        this.players = new Collection();
        this.winners = new Collection();
        this.losers = new Collection();
        this.bets = new Collection();
        this.state = Table.STATES.Unloaded;
        this.paused = false;
        this.deck = new Deck();

    }

    get minBet() { return this.settings.minBet; }
    get maxBet() { return this.settings.maxBet; }
    get minPlayers() { return this.settings.minPlayers; }
    get maxPlayers() { return this.settings.maxPlayers; }
    get bettingTime() { return this.settings.bettingTime; }
    get lobbyTime() { return this.settings.lobbyTime; }

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
        Cancelled: 'cancelled',
        Playing: 'playing',
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
            this.bets = new Collection(Object.entries(data.bets));
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
        const bets = {};
        for (const [key, value] of this.bets) {
            bets[key] = value;
        }
        return {
            channelId: this.channel.id,
            guildId: this.casino.id,
            messageId: this.id,
            gameId: this.gameId,
            messages: this.messages.map(m => m.id),
            players:this.players.map(p => p.id),
            bets: bets,
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
        if (this.State === Table.STATES.Lobby) {
            const embed = new MessageEmbed()
                .setColor(COLOR.creation)
                .setTitle(`Lobby for ${this.name}`)
                .setDescription(this.description)
                .setFooter(`Table ID: ${this.id}`)
                .addField('Players', playerString ? playerString : 'None', true)
                .addField('Technical Info', `Max Players: **${this.maxPlayers}**\nMinimum Players: **${this.minPlayers}**` +
                `\n\nMaximum Bet: **${this.maxBet}**\nMinimum Bet: **${this.minBet}**`, true);
            embeds.push(embed);
        } else if (this.State === Table.STATES.Paused) {
            const embed = new MessageEmbed()
                .setColor(COLOR.creation)
                .setTitle(`${this.name} Paused`)
                .setDescription('The game is currently paused.')
                .setFooter(`Table ID: ${this.id}`)
                .addField('Players', playerString ? playerString : 'None', true);
            embeds.push(embed);
        } else if (this.State === Table.STATES.Betting) {
            const betString = this.players.map(p => `${userMention(p.id)} - ${this.bets.get(p.id) ?? 'None'}`).join('\n');
            const embed = new MessageEmbed()
                .setColor(COLOR.creation)
                .setTitle(`Betting for ${this.name}`)
                .setDescription('Place your bets below.')
                .setFooter(`Table ID: ${this.id}`)
                .addField('Players', betString ? betString : 'None', true);
            embeds.push(embed);
        } else if (this.State === Table.STATES.Playing) {
            const embed = new MessageEmbed()
                .setColor(COLOR.creation)
                .setTitle(`Playing ${this.name}`)
                .setDescription('Invalid Game.');
        }
        return embeds;
    }

    getComponents() {
        const components = [];
        if (this.State === Table.STATES.Lobby) {
            const startable = ((this.maxPlayers - this.minPlayers) / 2) <= (this.players.size - this.minPlayers);
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
                        .setDisabled(!startable),
                );
            components.push(row);
            components.push(row2);
        } else if (this.State === Table.STATES.Paused) {
            const row = new MessageActionRow()
                .addComponents(
                    new MessageButton()
                        .setCustomId('casinoTableResume')
                        .setLabel('Resume')
                        .setStyle('SUCCESS'),
                );
            components.push(row);
        } else if (this.State === Table.STATES.Betting) {
            const increment = Math.floor((this.maxBet - this.minBet) / 10);
            const options = [];
            for (let i = 0; i <= 10; i++) {
                options.push({
                    label: `${this.minBet + (i * increment)} Coins`,
                    description: `Bet ${this.minBet + (i * increment)} coins`,
                    value: `${this.minBet + (i * increment)}`,
                });
            }
            const row = new MessageActionRow()
                .addComponents(
                    new MessageSelectMenu()
                        .setCustomId('casinoTableBet')
                        .setPlaceholder('Select Bet Amount')
                        .addOptions(options),
                );
            components.push(row);
        }
        return components;
    }

    scheduleRun(time, callback = this.run, override = false) {
        if (override) {
            this.stopRun();
            this.runProcess = setTimeout(callback, time);
        } else if (!this.runProcess) {
            this.runProcess = setTimeout(callback, time);
        }
    }

    stopRun() {
        if (this.runProcess) {
            clearTimeout(this.runProcess);
            this.runProcess = null;
        }
    }

    async startBetting() {
        this.stopRun();
        this.State = Table.STATES.Betting;
        this.scheduleRun(this.bettingTime, this.startPlaying);
        await this.save();
    }

    async startPlaying() {
        this.stopRun();
        this.State = Table.STATES.Playing;
        await this.save();
    }

    async run(interaction = null) {
        // TODO: Implement
        this.stopRun();
    }

    async cancel() {
        this.stopRun();
        this.state = Table.STATES.Cancelled;

    }

    async join(player) {
        if (this.players.has(player.id) || player.Table) return false;
        this.players.set(player.id, player);
        player.Table = this;
        await this.save();
        return true;
    }

    async leave(player) {
        if (!this.players.has(player.id) && this.State === Table.STATES.Lobby) return false;
        this.players.delete(player.id);
        player.Table = null;
        await this.save();
        return true;
    }

    async handleInteraction(interaction) {
        console.log(`${this.id} Recieved Interaction`);
        if (interaction.customId === 'casinoTableJoin' && this.Joinable) {
            // Join Table
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
        } else if (interaction.customId === 'casinoTableLeave' && this.State === Table.STATES.Lobby) {
            // Leave Table
            const player = this.casino.getPlayer(interaction.user.id);
            if (!await this.leave(player)) {
                await interaction.reply({ content: 'You are not in this table.', components: [this.ReturnRow], ephemeral: true });
            } else {
                await this.updateMessage(undefined, undefined, interaction);
            }
        } else if (interaction.customId === 'casinoTableStart') {
            // Start Table
            if (this.Playable) {
                await this.startBetting();
                await this.updateMessage(undefined, undefined, interaction);
            } else {
                await interaction.reply({ content: 'You cannot start this game yet.', components: [this.ReturnRow], ephemeral: true });
            }
        } else if (interaction.customId === 'casinoTableBet' && this.State === Table.STATES.Betting) {
            // Bet
            const player = this.players.get(interaction.user.id);
            player.bet(parseInt(interaction.values[0]), this);
            await this.save();
            if (this.bets === this.players.size) {
                await this.startPlaying();
            }
            await this.updateMessage(undefined, undefined, interaction);
        }
    }

    async updateMessage(embeds = null, components = null, interaction = null) {
        if (!embeds) embeds = this.getEmbeds();
        if (!components) components = this.getComponents();
        const message = this.message;
        if (interaction && !interaction.replied) {
            await interaction.update({ content: null, components, embeds });
        } else {
            await message.edit({ content: null, embeds, components });
        }
    }
}

module.exports = {
    Table,
};