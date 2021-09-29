const { SlashCommandBuilder } = require('@discordjs/builders');
const { CategoryChannel, Permissions } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('editserver')
        .setDescription('Edits the server settings')
        .setDefaultPermission(false)
        .addChannelOption(option =>
            option.setName('topiccategory')
                .setDescription('The category that new topics appear in.'))
        .addChannelOption(option =>
            option.setName('archivecategory')
                .setDescription('The category that topics will be archived.'))
        .addRoleOption(option =>
            option.setName('startingrole')
                .setDescription('The role that users will be given when they join the server.'))
        .addChannelOption(option =>
            option.setName('quoteschannel')
                .setDescription('The channel that quotes will be posted in.'))
        .addStringOption(option =>
            option.setName('clear')
                .setDescription('Unsets one of the previous options.')
                .addChoice('Topic Category', 'topiccategory')
                .addChoice('Archive Category', 'archivecategory')
                .addChoice('Starting Role', 'startingrole')
                .addChoice('Quotes Channel', 'quoteschannel')),
    rolePermissions: [Permissions.FLAGS.MANAGE_CHANNELS],
    async execute(interaction) {
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS])) {
            return interaction.reply({ content: 'You do not have permission to edit the server.', ephemeral: true });
        }
        const server = interaction.client.servers.get(interaction.guild.id);
        const topicCategory = interaction.options.getChannel('topiccategory');
        const archiveCategory = interaction.options.getChannel('archivecategory');
        const startingRole = interaction.options.getRole('startingrole');
        const quotesChannel = interaction.options.getChannel('quoteschannel');
        const clearString = interaction.options.getString('clear');

        if (topicCategory && topicCategory instanceof CategoryChannel) {
            server.topicCategory = topicCategory;
        }
        if (archiveCategory && archiveCategory instanceof CategoryChannel) {
            server.archiveCategory = archiveCategory;
        }
        if (startingRole) {
            server.startingRole = startingRole;
        }
        if (quotesChannel && !(quotesChannel instanceof CategoryChannel)) {
            server.quotesChannel = quotesChannel;
        }
        if (clearString) {
            switch (clearString) {
            case 'topiccategory':
                server.topicCategory = null;
                break;
            case 'archivecategory':
                server.archiveCategory = null;
                break;
            case 'startingrole':
                server.startingRole = null;
                break;
            case 'quoteschannel':
                server.quotesChannel = null;
                break;
            }
        }

        await server.save();
        await interaction.reply({ content: 'Server settings updated.', ephemeral: true });
    },
};