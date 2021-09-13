const { MessageActionRow, MessageButton, MessageEmbed, Collection } = require('discord.js');
const { SlashCommandBuilder, userMention } = require('@discordjs/builders');
const { Deck, Hand, HandFinders } = require('../models/playingCards');
const { COLOR } = require('../models/colors');

const wait = require('util').promisify(setTimeout);
const bjRow = new MessageActionRow()
    .addComponents(
        new MessageButton()
            .setCustomId('bjHit')
            .setLabel('Hit')
            .setStyle('SUCCESS'),
        new MessageButton()
            .setCustomId('bjStay')
            .setLabel('Stay')
            .setStyle('DANGER'),
    );

const setCurrentTurn = (embed, currentTurn) => {
    const field = embed.fields.find(f => f.name === 'Current Turn');
    if (field) {
        field.value = userMention(currentTurn);
    } else {
        embed.addField('Current Turn', userMention(currentTurn));
    }
};

module.exports = {
    data: new SlashCommandBuilder()
        .setName('blackjack')
        .setDescription('Play some blackjack!'),
    async execute(interaction) {
        const SECONDS_TO_JOIN = 30;
        const SECONDS_TO_PLAY = 10;
        const server = interaction.client.servers.get(interaction.guild.id);
        const players = new Collection();
        const stayed = new Collection();
        const busted = new Collection();
        const winners = new Collection();
        const tied = new Collection();
        const bets = new Collection();
        players.set(interaction.member.id, [interaction.member, new Hand()]);
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('bjStart')
                    .setLabel('Start')
                    .setStyle('SUCCESS')
                    .setDisabled(true),
            );
        const row2 = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('bjBet10')
                    .setLabel('Bet 10')
                    .setStyle('SECONDARY'),
                new MessageButton()
                    .setCustomId('bjBet100')
                    .setLabel('Bet 100')
                    .setStyle('SECONDARY'),
                new MessageButton()
                    .setCustomId('bjBet500')
                    .setLabel('Bet 500')
                    .setStyle('SECONDARY'),
                new MessageButton()
                    .setCustomId('bjBet1000')
                    .setLabel('Bet 1,000')
                    .setStyle('SECONDARY'),
                new MessageButton()
                    .setCustomId('bjBet10000')
                    .setLabel('Bet 10,000')
                    .setStyle('SECONDARY'),
            );
        const embed = new MessageEmbed()
            .setColor(COLOR.creation)
            .setTitle('Welcome to Blackjack!')
            .setDescription('The goal of the game is to get as close to 21 as possible without going over. ' +
                'Beat the dealer to win.\n\n' +
                `This game can be played with 4 players at a time. You have ${SECONDS_TO_JOIN} seconds to join. If the host hits start then the game begins immediately.`);
        embed.addField('Players', userMention(players.firstKey()));
        const message = await interaction.reply({ embeds: [embed], components: [row, row2], fetchReply: true });
        const deck = new Deck();
        deck.addHand(players.first()[1]);
        let go = false;
        // Allow up to 4 people to join.
        while (go === false) {
            try {
                const joinInteraction = await message.awaitMessageComponent({ componentType: 'BUTTON', time: SECONDS_TO_JOIN * 1000 });
                if (joinInteraction.customId === 'bjStart') {
                    if (joinInteraction.member.id === interaction.user.id) {
                        go = true;
                    } else {
                        joinInteraction.reply({ content: 'You are not the host', ephemeral: true });
                    }
                } else if (['bjBet10', 'bjBet100', 'bjBet500', 'bjBet1000', 'bjBet10000'].includes(joinInteraction.customId)) {
                    if (!players.has(joinInteraction.member.id) && players.size < 4) {
                        const hand = new Hand();
                        players.set(joinInteraction.member.id, [joinInteraction.member, hand]);
                        deck.addHand(hand);
                    }
                    if (server.bets && players.has(joinInteraction.member.id)) {
                        const amt = parseInt(joinInteraction.customId.substr(5));
                        if (server.getDeck(joinInteraction.member).points >= amt) {
                            bets.set(joinInteraction.member.id, amt);
                            if (joinInteraction.member.id === interaction.user.id) row.components[0].setDisabled(false);
                        } else {
                            await joinInteraction.reply({ content: 'You do not have enough points', ephemeral: true });
                        }
                    }
                }
                if (players.size === 4) {
                    go = true;
                }
                embed.fields[0].value = players.map(([player, hand]) => { return `${player}: ${bets.get(player.id)}`; }).join('\n');
                if (joinInteraction.replied) {
                    await message.edit({ embeds: [embed], components: [row, row2] });
                } else {
                    await joinInteraction.update({ embeds: [embed], components: [row, row2] });
                }
            } catch (e) {
                console.log(e);
                if (bets.has(interaction.member.id)) {
                    break;
                } else {
                    return message.edit({ content: 'They game was canceled because the host did not choose a bet.', embeds: [] });
                }
            }
        }
        embed.addField('Shuffling the Deck', 'The game will start shortly.');
        row.components[0].setDisabled(true);
        await message.edit({ embeds: [embed], components: [row] });
        // Create Dealer Hand
        const dealerHand = new Hand();
        deck.addHand(dealerHand);
        // Shuffle and deal cards
        deck.shuffle();
        deck.deal(2);
        await wait(3000);
        const bjEmbed = new MessageEmbed()
            .setColor(COLOR.blackjack)
            .setTitle('Blackjack')
            .setDescription(`Dealers Cards: ${dealerHand.cards[0].toShortString()}, ?\nDealers Points: ${HandFinders.getBlackJackValue(dealerHand.cards[0])}`);
        for (const [player, hand] of players.values()) {
            const score = HandFinders.getBlackJackScore(hand.cards);
            if (score > 21) {
                busted.set(player.id, [player, hand]);
                players.delete(player.id);
            }
            bjEmbed.addField(`${player.displayName} ${busted.has(player.id) ? '(Busted)' : ''}`, `${hand.cards.map(c => c.toShortString()).join(', ')}\nPoints: ${score}`, true);
        }
        // Loop until all players have busted or stayed
        while (players.size > 0) {
            const currentTurn = players.first()[0].id;
            setCurrentTurn(bjEmbed, currentTurn);
            await message.edit({ embeds: [bjEmbed], components: [bjRow] });
            try {
                // Wait for a player to hit or stay
                const buttonInteraction = await message.awaitMessageComponent({ filter: inter => {
                    return inter.user.id === currentTurn;
                }, componentType: 'BUTTON', time: SECONDS_TO_PLAY * 1000 });
                await buttonInteraction.deferUpdate();
                // Get the player's hand and embed field
                const [ player, hand ] = players.get(currentTurn);
                const field = bjEmbed.fields.find(f => f.name.includes(player.displayName));
                if (buttonInteraction.customId === 'bjStay') {
                    // If the player stays, remove them from the players list
                    stayed.set(currentTurn, players.get(currentTurn));
                    players.delete(currentTurn);
                    field.name += ' (Stayed)';
                } else if (buttonInteraction.customId === 'bjHit') {
                    // If the player hits, deal them a card
                    hand.add(deck.draw());
                    const score = HandFinders.getBlackJackScore(hand.cards);
                    if (score > 21) {
                        // If the player busts, remove them from the players list
                        busted.set(currentTurn, players.get(currentTurn));
                        players.delete(currentTurn);
                        field.name += ' (Busted)';
                    }
                    // Update the player's hand in the field
                    field.value = `${hand.cards.map(c => c.toShortString()).join(', ')}\nPoints: ${score}`;
                }
            } catch (e) {
                // If the player doesn't respond, force them to stay
                const [ player, hand ] = players.get(currentTurn);
                stayed.set(player.id, [player, hand]);
                players.delete(player.id);
                const field = bjEmbed.fields.find(f => f.name.includes(player.displayName));
                field.name += ' (Stayed)';
                console.log(e);
            }
        }
        bjEmbed.description = 'Revealing Dealers Cards...';
        await message.edit({ embeds: [bjEmbed], components: [] });
        await wait(3000);
        // Dealers turn
        let dealerScore = HandFinders.getBlackJackScore(dealerHand.cards);
        while (dealerScore < 17) {
            dealerHand.add(deck.draw());
            dealerScore = HandFinders.getBlackJackScore(dealerHand.cards);
        }
        // Check if the dealer busted
        if (dealerScore > 21) {
            bjEmbed.description = `Dealer Busted!\n${dealerHand.cards.map(c => c.toShortString()).join(', ')}\nPoints: ${dealerScore}`;
            for (const [player, hand] of stayed.values()) {
                winners.set(player.id, [player, hand]);
                const field = bjEmbed.fields.find(f => f.name.includes(player.displayName));
                field.name += ' (Winner)';
            }
        } else {
            // Check if the dealer has a higher score than the players
            for (const [player, hand] of stayed.values()) {
                const field = bjEmbed.fields.find(f => f.name.includes(player.displayName));
                const playerScore = HandFinders.getBlackJackScore(hand.cards);
                if (dealerScore < playerScore) {
                    players.delete(player.id);
                    winners.set(player.id, [player, hand]);
                    field.name += ' (Winner)';
                } else if (dealerScore === playerScore) {
                    players.delete(player.id);
                    tied.set(player.id, [player, hand]);
                    field.name += ' (Tied)';
                } else {
                    busted.set(player.id, [player, hand]);
                    field.name += ' (Loser)';
                }
            }
            // Update the embed
            bjEmbed.description = `Dealer Cards: ${dealerHand.cards.map(c => c.toShortString()).join(', ')}\nDealer Points: ${dealerScore}`;
        }
        bjEmbed.fields.pop();
        await message.edit({ embeds: [bjEmbed], components: [] });
        await wait(3000);

        const losers = busted;
        const winnerEmbed = new MessageEmbed()
            .setColor(COLOR.blackjack)
            .setTitle('Winnings')
            .setDescription('Calculated winnings and loses.');
        for (const [player, hand] of winners.values()) {
            const bet = bets.get(player.id);
            const winnings = bet * 2;
            const pDeck = server.getDeck(player);
            pDeck.addPoints(winnings);
            winnerEmbed.addField(`${player.displayName}`, `Winnings: ${winnings}\nTotal Points: ${pDeck.points}`);
        }
        for (const [player, hand] of tied.values()) {
            const bet = bets.get(player.id);
            const winnings = bet;
            const pDeck = server.getDeck(player);
            winnerEmbed.addField(`${player.displayName}`, `Winnings: ${winnings}\nTotal Points: ${pDeck.points}`);
        }
        for (const [player, hand] of losers.values()) {
            const bet = bets.get(player.id);
            const loses = bet;
            const pDeck = server.getDeck(player);
            pDeck.spendPoints(loses);
            winnerEmbed.addField(`${player.displayName}`, `Losings: ${loses}\nTotal Points: ${pDeck.points}`);
        }
        await message.edit({ embeds: [bjEmbed, winnerEmbed], components: [] });
    },
};