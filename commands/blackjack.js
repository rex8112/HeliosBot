const { MessageActionRow, MessageButton, MessageEmbed, Collection } = require('discord.js');
const { SlashCommandBuilder, userMention } = require('@discordjs/builders');
const { Deck, Hand, HandFinders } = require('../models/playingCards');

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
        const players = new Collection();
        const stayed = new Collection();
        const busted = new Collection();
        const winners = new Collection();
        const tied = new Collection();
        players.set(interaction.member.id, [interaction.member, new Hand()]);
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('bjJoin')
                    .setLabel('Join')
                    .setStyle('PRIMARY'),
            );
        const embed = new MessageEmbed()
            .setColor('ORANGE')
            .setTitle('Welcome to Blackjack!')
            .setDescription('The goal of the game is to get as close to 21 as possible without going over. ' +
                'Beat the dealer to win.\n\n' +
                `This game can be played with 4 players at a time. You have ${SECONDS_TO_JOIN} seconds to join. If the host hits join then the game begins immediately.`);
        embed.addField('Players', userMention(players.firstKey()));
        const message = await interaction.reply({ embeds: [embed], components: [row], fetchReply: true });
        const deck = new Deck();
        deck.addHand(players.first()[1]);
        // Allow up to 4 people to join.
        for (let i = 0; i < 3; i++) {
            try {
                const joinInteraction = await message.awaitMessageComponent({ filter: inter => {
                    return !players.has(inter.member.id) || inter.member.id === interaction.user.id;
                },
                componentType: 'BUTTON', time: SECONDS_TO_JOIN * 1000 });
                if (joinInteraction.member.id === interaction.user.id) {
                    embed.addField('Shuffling the Deck', 'The game will start shortly.');
                    row.components[0].setDisabled(true);
                    await joinInteraction.update({ embeds: [embed], components: [row] });
                    break;
                }
                const hand = new Hand();
                players.set(joinInteraction.member.id, [joinInteraction.member, hand]);
                deck.addHand(hand);
                if (i === 2) {
                    row.components[0].setDisabled(true);
                    embed.addField('Shuffling the Deck', 'The game will start shortly.');
                }
                embed.fields[0].value += `\n${userMention(joinInteraction.user.id)}`;
                await joinInteraction.update({ embeds: [embed], components: [row] });
            } catch (e) {
                console.log(e);
                break;
            }
        }
        await wait(3000);
        const bjEmbed = new MessageEmbed()
            .setColor('ORANGE')
            .setTitle('Blackjack')
            .setDescription('Dealers Cards: ?, ?\nDealers Points: ?');
        // Create Dealer Hand
        const dealerHand = new Hand();
        deck.addHand(dealerHand);
        // Shuffle and deal cards
        deck.shuffle();
        deck.deal(2);
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
            }
        } else {
            // Check if the dealer has a higher score than the players
            for (const [player, hand] of stayed.values()) {
                const field = bjEmbed.fields.find(f => f.name.includes(player.displayName));
                const playerScore = HandFinders.getBlackJackScore(hand.cards);
                if (dealerScore < playerScore) {
                    winners.set(player.id, [player, hand]);
                    field.name += ' (Winner)';
                } else if (dealerScore === playerScore) {
                    tied.set(player.id, [player, hand]);
                    field.name += ' (Tied)';
                }
            }
            // Update the embed
            bjEmbed.description = `Dealer Cards: ${dealerHand.cards.map(c => c.toShortString()).join(', ')}\nDealer Points: ${dealerScore}`;
        }
        bjEmbed.fields.pop();
        await message.edit({ embeds: [bjEmbed], components: [] });
    },
};