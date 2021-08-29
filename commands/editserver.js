const { SlashCommandBuilder } = require('@discordjs/builders');
const { CategoryChannel } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('editserver')
        .setDescription('Edits the server settings')
        .addChannelOption(option =>
            option.setName('topiccategory')
                .setDescription('The category that new topics appear in.')),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        const topicCategory = interaction.options.getChannel('topiccategory');

        if (topicCategory && topicCategory instanceof CategoryChannel) {
            server.topicCategory = topicCategory;
        }

        await server.save();
        await interaction.reply('Server settings updated.', { ephemeral: true });
    },
};