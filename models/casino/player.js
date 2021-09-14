class Player {
    constructor(casino, member) {
        this.casino = casino;
        this.id = member.id;
        this.member = member;
        this.balance = 0;
        this.hand = null;
        this.game = null;
    }
}