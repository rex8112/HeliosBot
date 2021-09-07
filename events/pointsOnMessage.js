const { Server } = require('../models/server');

module.exports = {
    name: 'messageCreate',
    async execute(message) {
        try {
            if (message.author.bot) return;
            if (message.channel.type === 'DM') return;

            const server = message.client.servers.get(message.guild.id);
            let deck = server.decks.get(message.author.id);
            if (!deck) deck = await server.newDeck(message.member);
            deck.addMessagePoints(Server.POINTS_PER_MESSAGE);
        } catch (error) {
            console.error(error);
        }
    },
};