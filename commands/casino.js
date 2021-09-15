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
                        .setRequired(true))),
    rolePermissions: [Permissions.FLAGS.MANAGE_GUILD],
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        let casino = server.casino;
        if (!casino) server.casino = casino = await new Casino(server).load();
        if (interaction.options.getSubcommand() === 'addchannel') {
            const channel = interaction.options.getChannel('channel');
            await casino.addChannel(channel);
            return interaction.reply({ content: `Added ${channel.name} to the casino`, ephemeral: true });
        }
    },
};