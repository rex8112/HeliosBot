const { Deck: DeckDB } = require('../tools/database');

class Deck {
    constructor(server, member) {
        this.server = server;
        this.guild = server.guild;
        this.member = member;
        this.cards = {};
        this.totalPoints = 0;
        this.spentPoints = 0;
        this.lastMessageTime = Date.now();
    }

    get points() { return this.totalPoints - this.spentPoints; }

    toJSON() {
        return {
            guildId: this.guild.id,
            userId: this.member.id,
            cards: this.cards,
            totalPoints: this.totalPoints,
            spentPoints: this.spentPoints,
        };
    }

    async insert() {
        await DeckDB.create(this.toJSON());
    }

    async save() {
        return await DeckDB.update(this.toJSON(), { where: { guildId: this.guild.id, userId: this.member.id } });
    }

    async load() {
        const deck = await DeckDB.findOne({ where: { guildId: this.guild.id, userId: this.member.id } });
        if (deck) {
            this.cards = deck.cards;
            this.totalPoints = deck.totalPoints;
            this.spentPoints = deck.spentPoints;
        } else {
            this.insert();
        }
        return this;
    }

    async addPoints(points) {
        this.totalPoints += points;
        await this.save();
    }

    async spendPoints(points) {
        if (this.points < points) return false;
        this.spentPoints += points;
        await this.save();
        return true;
    }

    async addMessagePoints(points) {
        if (this.lastMessageTime + 60 * 1000 < Date.now()) {
            this.lastMessageTime = Date.now();
            await this.addPoints(points);
        }
    }

    static async getAllFromGuild(server) {
        const decksData = await DeckDB.findAll({ where: { guildId: server.guild.id } });
        const decks = [];
        for (const deckData of decksData) {
            const member = await server.guild.members.fetch(deckData.userId);
            if (member) {
                const deck = new Deck(server, member).load();
                decks.push(deck);
            }
        }
        return decks;
    }

    compareToDeck(deck) {
        return this.totalPoints - deck.totalPoints;
    }
}

module.exports = {
    Deck,
};