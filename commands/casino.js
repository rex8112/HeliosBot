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
                .setDescription('Add a channel to the casino.')
                .addChannelOption(option =>
                    option
                        .setName('channel')
                        .setDescription('The channel to add.')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('addtable')
                .setDescription('Add a table to the current casino channel.')
                .addStringOption(option =>
                    option
                        .setName('table')
                        .setDescription('Add a new table to the current channel.')
                        .setRequired(true)
                        .addChoice('Blackjack', 'Blackjack'))
                .addIntegerOption(option =>
                    option
                        .setName('minBet')
                        .setDescription('The minimum bet for the table.')
                        .setRequired(true))
                .addIntegerOption(option =>
                    option
                        .setName('maxBet')
                        .setDescription('The maximum bet for the table.')
                        .setRequired(true))
                .addIntegerOption(option =>
                    option
                        .setName('maxPlayers')
                        .setDescription('The maximum number of players for the table.')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('refresh')
                .setDescription('Refresh the casino')),
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
            const cc = casino.channels.get(interaction.channel.id);
            if (!cc) return interaction.reply({ content: 'You must be in a casino channel to add a table.', ephemeral: true });
            const gameId = interaction.options.getString('table');
            const settings = {
                minBet: interaction.options.getInteger('minBet'),
                maxBet: interaction.options.getInteger('maxBet'),
                maxPlayers: interaction.options.getInteger('maxPlayers'),
            };
            await cc.createTable(gameId, settings);
            return interaction.editReply({ content: 'Added a table', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'refresh') {
            await interaction.deferReply({ ephemeral: true });
            await casino.refreshChannels();
            return interaction.editReply({ content: 'Casino Refreshed', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'addblackjack') {
            await interaction.deferReply({ ephemeral: true });
            await casino.channels.get(interaction.channel.id).createTable('Blackjack');
            return interaction.editReply({ content: 'Added a blackjack table', ephemeral: true });
        }
    },
};