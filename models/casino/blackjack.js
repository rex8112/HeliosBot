const { Collection, MessageEmbed, MessageActionRow, MessageButton } = require('discord.js');

const { Table } = require('./table');
const { Hand, HandFinders } = require('../playingCards');
const { COLOR } = require('../colors');

const wait = require('util').promisify(setTimeout);

class BlackjackTable extends Table {
    constructor(casino, message, settings = {}) {
        super(casino, message, settings);

        this.gameId = 'Blackjack';
        this.name = 'Blackjack Table';
        this.description = 'The goal of the game is to get as close to 21 as possible without going over. ' +
        'Beat the dealer to win. Ties pay back 1:1.\n\n';

        this.dealer = new Hand();
        this.showDealer = false;
        this.dealerString = '';
        this.playerStatus = new Collection();
        this.currentTurn = 0;
        this.turnOrder = new Array();
        this.settings.lobbyTime = 15000;
        this.settings.endTime = 10000;
        this.settings['turnTimer'] = 15000;
    }

    get CurrentTurn() { return this.players.get(this.turnOrder[this.currentTurn]); }

    async startPlaying() {
        this.deck.reset();
        this.deck.clearHands();
        for (const player of this.players.values()) {
            this.deck.addHand(player.hand);
            this.playerStatus.set(player.id, { status: 'playing', victory: undefined, winnings: 0 });
        }
        this.deck.addHand(this.dealer);
        this.deck.shuffle();
        this.deck.deal(2);
        this.dealerString = `${this.dealer.cards[0].toShortString()}, ?`;
        this.currentTurn = 0;
        this.turnOrder = Array.from(this.players.keys());
        await super.startPlaying();
        this.scheduleRun(this.settings.turnTimer);
    }

    async cleanup(returnBets = false) {
        this.deck.reset();
        this.deck.clearHands();
        this.playerStatus.clear();
        this.showDealer = false;
        await super.cleanup(returnBets);
    }

    async endTable() {
        this.dealerString = this.dealer.toShortString();
        this.showDealer = true;
        await this.updateMessage();
        await wait(2000);
        while (HandFinders.getBlackJackScore(this.dealer.cards) < 17) {
            this.dealer.add(this.deck.draw());
            this.dealerString = this.dealer.toShortString();
            await this.updateMessage();
            await wait(2000);
        }
        for (const player of this.players.values()) {
            this.checkWin(player);
            player.pay(this.playerStatus.get(player.id).winnings);
        }
        await this.updateMessage();
        await wait(3000);
        await super.endTable();
    }

    checkBust(player) {
        const value = HandFinders.getBlackJackScore(player.hand.cards);
        if (value > 21) {
            const status = this.playerStatus.get(player.id);
            status.status = 'Bust';
            status.victory = false;
            this.nextTurn();
            return true;
        }
        return false;
    }

    checkWin(player) {
        const value = HandFinders.getBlackJackScore(player.hand.cards);
        const dealerValue = HandFinders.getBlackJackScore(this.dealer.cards);
        const status = this.playerStatus.get(player.id);
        if (status.status === 'Bust') {
            status.victory = false;
            status.winnings = this.getWinning(player, false);
            return false;
        } else if (dealerValue > 21) {
            status.victory = true;
            status.winnings = this.getWinning(player, true);
            return true;
        } else if (value > dealerValue) {
            status.victory = true;
            status.winnings = this.getWinning(player, true);
            return true;
        } else if (value === dealerValue) {
            status.victory = null;
            status.winnings = this.getWinning(player, null);
            return null;
        } else {
            status.victory = false;
            status.winnings = this.getWinning(player, false);
            return false;
        }
    }

    getWinning(player, victory) {
        let betAmount = this.bets.get(player.id);
        if (victory === true) {
            betAmount *= 2;
        } else if (victory === false) {
            betAmount = 0;
        }
        return betAmount;
    }

    hit(member) {
        const player = this.players.get(member.id);
        player.hand.add(this.deck.draw());
        this.scheduleRun(this.settings.turnTimer, true);
        this.checkBust(player);
    }

    stay(member) {
        const player = this.players.get(member.id);
        this.playerStatus.get(player.id).status = 'Stayed';
        this.scheduleRun(this.settings.turnTimer, true);
        this.nextTurn();
    }

    nextTurn() {
        this.currentTurn++;
        if (this.currentTurn >= this.turnOrder.length) {
            this.currentTurn = -1;
            this.scheduleRun(2000, true);
        }
    }

    getVictoryString(player) {
        const status = this.playerStatus.get(player.id);
        let victory = '';
        if (status.victory === true) {
            victory = '**Win!**';
        } else if (status.victory === false) {
            victory = '**Lose!**';
        } else if (status.victory === null) {
            victory = '**Tie!**';
        } else {
            victory = '**Playing...**';
        }
        victory += ` ${status.status != 'playing' ? status.status : ''}`;
        return victory;
    }

    getEmbeds() {
        const embeds = [];
        if (this.State === Table.STATES.Playing || this.State === Table.STATES.Ended) {
            const dealerValue = this.showDealer ? HandFinders.getBlackJackScore(this.dealer.cards) : HandFinders.getBlackJackValue(this.dealer.cards[0]);
            const blackjackEmbed = new MessageEmbed()
                .setColor(COLOR.blackjack)
                .setTitle(this.name)
                .setDescription(`Dealer Cards: ${this.dealerString}\nDealer Points: ${dealerValue}`);
            for (const player of this.players.values()) {
                const handString = player.hand.toShortString();
                const value = HandFinders.getBlackJackScore(player.hand.cards);
                const victory = this.getVictoryString(player);
                blackjackEmbed.addField(`${player.member.displayName}'s Cards`, `${handString}\nPoints: ${value}\nStatus: ${victory}`, true);
            }
            if (this.currentTurn >= 0) {
                blackjackEmbed.addField('Current Turn', `${this.CurrentTurn.member}`, false);
            }
            embeds.push(blackjackEmbed);

            // Show winnings if the table ended
            if (this.State === Table.STATES.Ended) {
                const winningsEmbed = new MessageEmbed()
                    .setColor(COLOR.result)
                    .setTitle('Winnings')
                    .setDescription('Calculated winnings and loses.');
                for (const player of this.players.values()) {
                    const status = this.playerStatus.get(player.id);
                    const bet = this.bets.get(player.id);
                    const winnings = status.winnings;
                    winningsEmbed.addField(`${player.member.displayName}`, `Winnings: ${winnings}\n\nAmount Bet: ${bet}\nPoints: ${player.balance}`, true);
                }
                embeds.push(winningsEmbed);
            }
        } else {
            return super.getEmbeds();
        }
        return embeds;
    }

    getComponents() {
        const components = [];
        if (this.State === Table.STATES.Playing) {
            const row = new MessageActionRow()
                .addComponents(
                    new MessageButton()
                        .setCustomId('casinoTableHit')
                        .setLabel('Hit')
                        .setStyle('SUCCESS'),
                    new MessageButton()
                        .setCustomId('casinoTableStay')
                        .setLabel('Stay')
                        .setStyle('DANGER'),
                );
            components.push(row);
        } else {
            return super.getComponents();
        }
        return components;
    }

    async run(interaction = null) {
        this.stopRun();
        if (this.State === Table.STATES.Playing) {
            // Check if there are any players left to play
            if (this.currentTurn === -1) {
                await this.endTable();
            } else {
                const player = this.CurrentTurn;
                this.stay(player.member);
            }
        } else {
            return super.run(interaction);
        }
        await this.updateMessage();
    }

    async handleInteraction(interaction) {
        if (interaction.customId === 'casinoTableHit') {
            this.hit(interaction.member);
        } else if (interaction.customId === 'casinoTableStay') {
            this.stay(interaction.member);
        } else {
            return super.handleInteraction(interaction);
        }
        this.updateMessage(undefined, undefined, interaction);
    }
}

Table.TABLES.set(BlackjackTable.gameId, BlackjackTable);

module.exports = {
    BlackjackTable,
};