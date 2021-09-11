const { MessageActionRow, MessageButton, MessageEmbed, Collection } = require('discord.js');
const { SlashCommandBuilder, userMention } = require('@discordjs/builders');
const { Deck, Hand, HandFinders } = require('../models/playingCards');

const wait = require('util').promisify(setTimeout);
const bjRow = new MessageActionRow()
    .addComponents(
        new MessageButton()
            .setCustomId('bjHit')
            .setText('Hit')
            .setStyle('SUCCESS'),
        new MessageButton()
            .setCustomId('bjStay')
            .setText('Stay')
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
        players.set(interaction.author.id, [interaction.author, new Hand()]);
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('bjJoin')
                    .setText('Join')
                    .setStyle('PRIMARY'),
            );
        const embed = new MessageEmbed()
            .setColor('ORANGE')
            .setTitle('Blackjack')
            .setDescription('Welcome to Blackjack!\n\n' +
                'The goal of the game is to get as close to 21 as possible without going over. ' +
                'Beat the dealer to win.\n\n' +
                `This game can be played with 4 players at a time. You have ${SECONDS_TO_JOIN} seconds to join. If the host hits join then the game begins immediately.`);
        const message = await interaction.reply({ embeds: [embed], components: [row] });
        const deck = new Deck();
        deck.addHand(players.first().value[1]);
        embed.addField('Players', userMention(players.first().key));
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
                break;
            }
        }
        await wait(3000);
        const bjEmbed = new MessageEmbed()
            .setColor('ORANGE')
            .setTitle('Blackjack')
            .setDescription('Dealers Cards: ?, ?\nDealers Points: ?');
        const dealerHand = new Hand();
        deck.addHand(dealerHand);
        deck.shuffle();
        deck.deal(2);
        for (const [player, hand] of players.values()) {
            const score = HandFinders.getBlackJackScore(hand.cards);
            if (score > 21) {
                busted.set(player.id, [player, hand]);
                players.delete(player.id);
            }
            bjEmbed.addField(`${player.displayName} ${busted.has(player.id) ? 'Busted' : ''}`, `${hand.cards.map(c => c.toString()).join(', ')}\nPoints: ${score}`);
        }
        while (players.size > 0) {
            const currentTurn = players.first().value[0].id;
            setCurrentTurn(bjEmbed, currentTurn);
            await message.edit({ embeds: [bjEmbed], components: [bjRow] });
            try {
                const buttonInteraction = await message.awaitMessageComponent({ filter: inter => {
                    return inter.user.id === currentTurn;
                }, componentType: 'BUTTON', time: SECONDS_TO_PLAY * 1000 });
                const { player, hand } = players.get(currentTurn);
                const field = bjEmbed.fields.find(f => f.name.includes(player.displayName));
                if (buttonInteraction.customId === 'bjStay') {
                    stayed.set(currentTurn, players.get(currentTurn));
                    players.delete(currentTurn);
                } else if (buttonInteraction.customId === 'bjHit') {
                    hand.add(deck.draw());
                    const score = HandFinders.getBlackJackScore(hand.cards);
                    if (score > 21) {
                        busted.set(currentTurn, players.get(currentTurn));
                        players.delete(currentTurn);
                    }
                    field.value = `${hand.cards.map(c => c.toString()).join(', ')}\nPoints: ${score}`;
                }
            } catch (e) {
                const { player, hand } = players.get(currentTurn);
                stayed.set(player.id, [player, hand]);
                players.delete(player.id);
                console.log(e);
            }
        }
        await message.edit({ embeds: [bjEmbed], components: [] });
    },
};