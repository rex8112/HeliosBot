const { SlashCommandBuilder } = require('@discordjs/builders');
const { VoiceLast } = require('../models/voice');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('voice')
        .setDescription('Build a private voice channel!')
        .addSubcommand(subcommand =>
            subcommand
                .setName('edit')
                .setDescription('Create a new voice channel')
                .addStringOption(option =>
                    option
                        .setName('name')
                        .setDescription('The name of the voice channel'))
                .addStringOption(option =>
                    option
                        .setName('type')
                        .setDescription('Whether the member list is whitelist or blacklist')
                        .addChoice('whitelist', 'whitelist')
                        .addChoice('blacklist', 'blacklist'))),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        if (!server.privateCategory) return interaction.reply({ content: 'This Discord needs a "Private Channels" Category first', ephemeral: true });
        if (interaction.options.getSubcommand() === 'edit') {
            await interaction.deferReply({ ephemeral: true });
            const name = interaction.options.getString('name');
            let typeString = interaction.options.getString('type');
            const voice = server.privateVoiceChannels.find(c => c.creator.id === interaction.member.id);
            if (typeString) typeString = typeString === 'whitelist' ? true : false;
            if (voice) {
                await voice.edit({ name, whitelist: typeString });
                await interaction.editReply({ content: 'Voice channel edited!' });
            } else {
                await interaction.editReply({ content: 'You do not have a voice channel.' });
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
        }
    },
};