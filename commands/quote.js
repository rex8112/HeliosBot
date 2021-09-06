const { SlashCommandBuilder } = require('@discordjs/builders');
const { Quote } = require('../models/quote');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('quote')
        .setDescription('Search up random quotes.')
        .addStringOption(option =>
            option
                .setName('id')
                .setDescription('The ID of the quote to search for.')
                .setRequired(false))
        .addUserOption(option =>
            option
                .setName('poster')
                .setDescription('The poster of the quote to search for.')
                .setRequired(false))
        .addUserOption(option =>
            option
                .setName('speaker')
                .setDescription('The speaker of the quote to search for.')
                .setRequired(false)),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        if (!server.quotesChannel) return interaction.reply({ content: 'Quotes are currently disabled on this server.', ephemeral: true });
        const id = interaction.options.getString('id');
        const poster = interaction.options.getMember('poster');
        const speaker = interaction.options.getMember('speaker');
        const quote = await Quote.getQuote(poster?.id, speaker?.id, id);
        if (quote) {
            return interaction.reply({ embeds: [await quote.toEmbed(interaction.client)] });
        }
        return interaction.reply('No quote found.');
    },
};