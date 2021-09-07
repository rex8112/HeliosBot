const { Quote } = require('../models/quote');

module.exports = {
    name: 'messageCreate',
    async execute(message) {
        try {
            if (message.author.bot) return;
            if (message.channel.type === 'DM') return;
            const server = message.client.servers.get(message.guild.id);
            if (message.channel.id === server.quotesChannel?.id) {
                await Quote.newQuote(message.author, message);
                await message.react('✅');
            }
        } catch (error) {
            console.error(error);
        }
    },
};