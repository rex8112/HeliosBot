const { SlashCommandBuilder } = require('@discordjs/builders');
const { Permissions } = require('discord.js');
const { Casino } = require('../models/casino/casino');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('casino')
        .setDescription('Manage Casino Settings')
        .addSubcommand(subcommand =>
            subcommand
                .setName('addchannel')
                .setDescription('Add a channel to the casino')
                .addChannelOption(option =>
                    option
                        .setName('channel')
                        .setDescription('The channel to add')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('addtable')
                .setDescription('Add a table to the casino. TESTING'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('refresh')
                .setDescription('Refresh the casino'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('createplayer')
                .setDescription('Create a player')),
    rolePermissions: [Permissions.FLAGS.MANAGE_GUILD],
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        let casino = server.casino;
        if (!casino) server.casino = casino = await new Casino(server).load();
        if (interaction.options.getSubcommand() === 'addchannel') {
            const channel = interaction.options.getChannel('channel');
            await casino.addChannel(channel);
            return interaction.reply({ content: `Added ${channel.name} to the casino`, ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'addtable') {
            await interaction.deferReply({ ephemeral: true });
            await casino.channels.get(interaction.channel.id).createTable('Testing');
            return interaction.editReply({ content: 'Added a table', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'refresh') {
            await interaction.deferReply({ ephemeral: true });
            await casino.refreshChannels();
            return interaction.editReply({ content: 'Casino Refreshed', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'createplayer') {
            await interaction.deferReply({ ephemeral: true });
            await casino.createPlayer(interaction.user);
            return interaction.editReply({ content: 'Player Created', ephemeral: true });
        }
    },
};