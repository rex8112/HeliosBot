const { default: Collection } = require('@discordjs/collection');
const { Player: PlayerDB } = require('../../tools/database');
const { Hand } = require('../playingCards');

class Player {
    constructor(casino, member) {
        this.casino = casino;
        this.id = member.id;
        this.member = member;
        this.balance = 0;
        this.hand = new Hand();
        this.tableId = null;
        this.dailyId = 0;
    }

    get Table() {
        return this.tableId ? this.casino.getTable(this.tableId) : null;
    }

    set Table(table) {
        this.tableId = table?.id ?? null;
        this.save();
    }

    static async fromCasino(casino) {
        const players = new Collection();
        const data = await PlayerDB.findAll({ where: { guildId: casino.id } });
        for (const playerData of data) {
            const member = await casino.server.guild.members.fetch(playerData.userId);
            const player = new Player(casino, member);
            await player.load(playerData);
            players.set(player.id, player);
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
            this.tableId = data.table;
            this.dailyId = data.dailyId;
        }

        return this;
    }

    async save() {
        // TODO: save to database
        const data = await PlayerDB.findOne({ where: { guildId: this.casino.id, userId: this.id } });
        if (data) {
            await PlayerDB.update(this.toJSON(), { where: { guildId: this.casino.id, userId: this.id } });
        } else {
            await PlayerDB.create(this.toJSON());
        }
    }

    toJSON() {
        return {
            guildId: this.casino.id,
            userId: this.id,
            balance: this.balance,
            hand: this.hand,
            table: this.tableId || null,
            dailyId: this.dailyId,
        };
    }

    toString() {
        return `${this.member}`;
    }

    async bet(amount, table = null) {
        if (table?.bets.has(this.id)) {
            await this.pay(table.bets.get(this.id), false);
        }
        if (amount > this.balance) {
            table?.bets.delete(this.id);
        } else {
            this.balance -= amount;
            table?.bets.set(this.id, amount);
        }
        await this.save();
    }

    async pay(amount, save = true) {
        this.balance += amount;
        if (save) {
            await this.save();
        }
    }


}

module.exports = {
    Player,
};