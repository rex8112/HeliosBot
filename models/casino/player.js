const { Player: PlayerDB } = require('../../tools/database');
const { Hand } = require('../playingCards');

class Player {
    constructor(casino, member) {
        this.casino = casino;
        this.id = member.id;
        this.member = member;
        this.balance = 0;
        this.hand = null;
        this.tableId = null;
    }

    get Table() {
        return this.casino.getTable(this.tableId);
    }

    static async fromCasino(casino) {
        const players = [];
        const data = await PlayerDB.findAll({ where: { guildId: casino.id } });
        for (const playerData of data) {
            const member = await casino.guild.members.fetch(playerData.userId);
            const player = new Player(casino, member);
            await player.load(playerData);
            players.push(player);
        }
        return players;
    }

    async load(data = null) {
        // TODO: load from database
        if (!data) {
            data = await PlayerDB.findOne({ where: { guildId: this.casino.id, userId: this.id } });
        }
        if (data) {
            this.balance = data.balance;
            this.hand = Hand.fromJSON(data.hand);
            this.tableId = data.tableId;
        }

        return this;
    }

    async save() {
        // TODO: save to database
        await PlayerDB.upsert(this.toJSON(), { where: { guildId: this.casino.id, userId: this.id } });
    }

    toJSON() {
        return {
            guildId: this.casino.id,
            userId: this.id,
            balance: this.balance,
            hand: this.hand,
            table: this.tableId?.id || null,
        };
    }

    toString() {
        return `${this.member}`;
    }
}

module.exports = {
    Player,
};