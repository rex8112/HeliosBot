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
                .setDescription('Triggers pending delete'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('sort')
                .setDescription('Sorts the topics'))
        .addSubcommand(subcommand =>
            subcommand
                .setName('pin')
                .setDescription('Pins the topic')),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        const topic = server.topics.get(interaction.channel.id);
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS]) && !topic.isOwner(interaction.member)) {
            return interaction.reply('You do not have permission to edit the topic.');
        }
        if (interaction.options.getSubcommand() === 'delete') {
            await interaction.deferReply({ ephemeral: true });
            await topic.delete(interaction.member);
        } else if (interaction.options.getSubcommand() === 'archive') {
            await interaction.deferReply({ ephemeral: true });
            await topic.archive();
            await interaction.editReply({ content: 'Topic archived.', ephemeral: true });
        } else if (interaction.options.getSubcommand() === 'triggerafk') {
            await interaction.deferReply({ ephemeral: true });
            await topic.queueArchive();
            await interaction.editReply({ content: 'Topic pending archive.', ephemeral: true });
        }
        // Subcommands that topic owners can't use
        if (interaction.member.permissions.has([Permissions.FLAGS.MANAGE_CHANNELS])) {
            if (interaction.options.getSubcommand() === 'sort') {
                await interaction.deferReply({ ephemeral: true });
                await server.sortTopicChannels();
                await interaction.editReply({ content: 'Topics sorted.', ephemeral: true });
            } else if (interaction.options.getSubcommand() === 'pin') {
                await interaction.deferReply();
                topic.pinned = topic.pinned ? false : true;
                await topic.save();
                await server.sortTopicChannels();
                await interaction.editReply({ content: 'Topic pinned.' });
            }
        }
    },
};