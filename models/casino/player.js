class Player {
    constructor(casino, member) {
        this.casino = casino;
        this.id = member.id;
        this.member = member;
        this.balance = 0;
        this.hand = null;
        this.table = null;
    }

    async load() {
        // TODO: load from database
        return this;
    }

    async save() {
        // TODO: save to database
    }

    toJSON() {
        return {
            guildId: this.casino.id,
            userId: this.id,
            balance: this.balance,
            hand: this.hand,
            table: this.table?.id || null,
        };
    }

    toString() {
        return `${this.member}`;
    }
}