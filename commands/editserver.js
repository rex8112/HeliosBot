const { SlashCommandBuilder } = require('@discordjs/builders');
const { CategoryChannel, Permissions } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('editserver')
        .setDescription('Edits the server settings')
        .addChannelOption(option =>
            option.setName('topiccategory')
                .setDescription('The category that new topics appear in.'))
        .addChannelOption(option =>
            option.setName('archivecategory')
                .setDescription('The category that topics will be archived.')),
    async execute(interaction) {
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS])) {
            return interaction.reply('You do not have permission to edit the server.');
        }
        const server = interaction.client.servers.get(interaction.guild.id);
        const topicCategory = interaction.options.getChannel('topiccategory');
        const archiveCategory = interaction.options.getChannel('archivecategory');

        if (topicCategory && topicCategory instanceof CategoryChannel) {
            server.topicCategory = topicCategory;
        }
        if (archiveCategory && archiveCategory instanceof CategoryChannel) {
            server.archiveCategory = archiveCategory;
        }

        await server.save();
        await interaction.reply({ content: 'Server settings updated.', ephemeral: true });
    },
};