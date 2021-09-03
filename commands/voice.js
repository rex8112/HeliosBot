const { SlashCommandBuilder } = require('@discordjs/builders');
const { VoiceLast } = require('../models/voice');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('voice')
        .setDescription('Build a private voice channel!')
        .addSubcommand(subcommand =>
            subcommand
                .setName('new')
                .setDescription('Create a new voice channel')
                .addStringOption(option =>
                    option
                        .setName('name')
                        .setDescription('The name of the voice channel')
                        .setRequired(true))
                .addStringOption(option =>
                    option
                        .setName('type')
                        .setDescription('Whether the member list is whitelist or blacklist')
                        .setRequired(true)
                        .addChoice('whitelist', 'whitelist')
                        .addChoice('blacklist', 'blacklist'))
                .addBooleanOption(option =>
                    option
                        .setName('nsfw')
                        .setDescription('Whether the channel is nsfw')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('last')
                .setDescription('Recreate the last voice channel')
                .addBooleanOption(option =>
                    option
                        .setName('nsfw')
                        .setDescription('Whether the channel is nsfw')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('delete')
                .setDescription('Delete your voice channel')),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        if (interaction.options.getSubcommand() === 'new') {
            const name = interaction.options.getString('name');
            const typeString = interaction.options.getString('type');
            const nsfw = interaction.options.getBoolean('nsfw');
            const type = typeString === 'whitelist' ? true : false;
            const channel = await server.newVoiceChannel(name, interaction.member, type, nsfw);
            if (channel.loaded) {
                await interaction.reply({ content: `Created voice channel ${channel.voiceChannel.name}`, ephemeral: true });
            } else {
                await interaction.reply({ content: 'Failed to create voice channel.', ephemeral: true });
            }
        } else if (interaction.options.getSubcommand() === 'delete') {
            const channel = server.privateVoiceChannels.get(interaction.channel.id);
            if (channel) {
                if (channel.creator.id === interaction.member.id) {
                    await channel.delete();
                    return interaction.reply('Deleted voice channel.');
                } else {
                    return interaction.reply('You are not the creator of this voice channel.');
                }
            } else {
                return interaction.reply('This is not a private channel.');
            }
        } else if (interaction.options.getSubcommand() === 'last') {
            const nsfw = interaction.options.getBoolean('nsfw');
            const voiceLast = await new VoiceLast(interaction.member).load();
            if (voiceLast.name) {
                const channel = await server.newVoiceChannel(voiceLast.name, interaction.member, voiceLast.whitelist, nsfw, voiceLast.members);
                if (channel.loaded) {
                    await interaction.reply({ content: `Created voice channel ${channel.voiceChannel.name}`, ephemeral: true });
                } else {
                    await interaction.reply({ content: 'Failed to create voice channel.', ephemeral: true });
                }
            }
        }
    },
};