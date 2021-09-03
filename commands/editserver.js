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
                .setDescription('The category that topics will be archived.'))
        .addRoleOption(option =>
            option.setName('startingrole')
                .setDescription('The role that users will be given when they join the server.')),
    async execute(interaction) {
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS])) {
            return interaction.reply('You do not have permission to edit the server.');
        }
        const server = interaction.client.servers.get(interaction.guild.id);
        const topicCategory = interaction.options.getChannel('topiccategory');
        const archiveCategory = interaction.options.getChannel('archivecategory');
        const startingRole = interaction.options.getRole('startingrole');

        if (topicCategory && topicCategory instanceof CategoryChannel) {
            server.topicCategory = topicCategory;
        }
        if (archiveCategory && archiveCategory instanceof CategoryChannel) {
            server.archiveCategory = archiveCategory;
        }
        if (startingRole) {
            server.startingRole = startingRole;
        }

        await server.save();
        await interaction.reply({ content: 'Server settings updated.', ephemeral: true });
    },
};