const { Collection, MessageEmbed } = require('discord.js');
const { userMention } = require('@discordjs/builders');
const { Deck } = require('../playingCards');
const { COLOR } = require('../colors');

class Table {
    constructor(casino, message) {
        this.casino = casino;
        this.id = message.id;
        this.channel = message.channel;
        this.messages = [message];

        this.name = 'Invalid Table';
        this.description = 'No description. Honestly, if you are seeing this outside of a testing environment then something is very wrong. Please do not bet anything.';

        this.players = new Collection();
        this.winners = new Collection();
        this.losers = new Collection();
        this.bets = new Collection();
        this.state = Table.STATES.Inactive;
        this.deck = new Deck();

        this.minBet = 0;
        this.maxBet = 0;
        this.maxPlayers = 0;
        this.minPlayers = 0;
    }

    get joinable() { return this.state === Table.STATES.Lobby; }

    static STATES = {
        Inactive: 'inactive',
        Lobby: 'lobby',
    }

    toJSON() {
        return {
            channelId: this.id,
            casinoId: this.casino.id,
            messages: this.messages.map(m => m.id),
            players:this.players,
            bets: this.bets,
            state: this.state,
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

    getLobbyEmbed() {
        const playerString = this.players.map(p => userMention(p.id)).join('\n');
        const embed = new MessageEmbed()
            .setColor(COLOR.creation)
            .setTitle(`Lobby for ${this.name}`)
            .setDescription(this.description)
            .setFooter(`Table ID: ${this.id}`)
            .addField('Players', playerString ? playerString : 'None', true)
            .addField('Technical Info', `Max Players: **${this.maxPlayers}\nMinimum Players: **${this.minPlayers}` +
            `\n\nMaximum Bet: **${this.maxBet}**\nMinimum Bet: **${this.minBet}**`, true);
        return embed;
    }
}