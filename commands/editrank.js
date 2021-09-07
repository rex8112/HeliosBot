const { SlashCommandBuilder } = require('@discordjs/builders');
const { Permissions } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('editrank')
        .setDescription('Edit a rank')
        .addSubcommand(subcommand =>
            subcommand
                .setName('add')
                .setDescription('Add a rank')
                .addRoleOption(option =>
                    option
                        .setName('role')
                        .setDescription('The role to add')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('remove')
                .setDescription('Remove a rank')
                .addRoleOption(option =>
                    option
                        .setName('role')
                        .setDescription('The role to remove')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('sort')
                .setDescription('Sort the ranks to match them in discord'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('setmember')
                .setDescription('Set the member rank')
                .addUserOption(option =>
                    option
                        .setName('member')
                        .setDescription('The member to set the rank for')
                        .setRequired(true))
                .addRoleOption(option =>
                    option
                        .setName('rank')
                        .setDescription('The rank to set the member to')
                        .setRequired(true))),
    permissions: [Permissions.FLAGS.MANAGE_ROLES],
    async execute(interaction) {
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS])) {
            return interaction.reply({ content: 'You do not have permission to use this command.', ephemeral: true });
        }
        const server = interaction.client.servers.get(interaction.guild.id);
        if (!server.theme) return;

        if (interaction.options.getSubcommand() === 'add') {
            if (server.theme.addRank(interaction.options.getRole('role'))) {
                return interaction.reply({ content: 'Rank added.', ephemeral: true });
            } else {
                return interaction.reply({ content: 'Rank already exists.', ephemeral: true });
            }
        } else if (interaction.options.getSubcommand() === 'remove') {
            if (server.theme.removeRank(interaction.options.getRole('role'))) {
                return interaction.reply({ content: 'Rank removed.', ephemeral: true });
            } else {
                return interaction.reply({ content: 'Rank not found.', ephemeral: true });
            }
        } else if (interaction.options.getSubcommand() === 'sort') {
            server.theme.sortRanks();
            return interaction.reply({ content: 'Ranks sorted.', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'setmember') {
            const rank = server.theme.getRank(interaction.options.getRole('rank'));
            if (!rank) return interaction.reply({ content: 'Rank not found.', ephemeral: true });
            const member = interaction.options.getMember('member');
            if (!member) return interaction.reply({ content: 'Member not found.', ephemeral: true });
            if (await server.theme.setMemberRank(member, rank)) {
                return interaction.reply({ content: 'Member rank set.', ephemeral: true });
            } else {
                return interaction.reply({ content: 'Member rank already set.', ephemeral: true });
            }
        }
    },
};