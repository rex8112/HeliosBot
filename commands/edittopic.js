const { SlashCommandBuilder } = require('@discordjs/builders');
const { Permissions } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('edittopic')
        .setDescription('Edits the topic')
        .addSubcommand(subcommand =>
            subcommand
                .setName('delete')
                .setDescription('Deletes the Topic PERMENANTLY'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('archive')
                .setDescription('Archives the Topic'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('triggerafk')
                .setDescription('Triggers pending delete')),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        const topic = server.topics.get(interaction.channel.id);
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS]) && !topic.isOwner(interaction.member)) {
            return interaction.reply('You do not have permission to edit the topic.');
        }
        if (interaction.options.getSubcommand() === 'delete') {
            await interaction.deferReply();
            await topic.delete(interaction.member);
        } else if (interaction.options.getSubcommand() === 'archive') {
            await interaction.deferReply();
            await topic.archive();
            await interaction.editReply({ content: 'Topic archived.', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'triggerafk') {
            await interaction.deferReply();
            await topic.queueArchive();
            await interaction.editReply({ content: 'Topic pending archive.', ephemeral: true });
        }
    },
};