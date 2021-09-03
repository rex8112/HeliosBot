module.exports = {
    data: {
        type: 2,
        name: 'Remove from Voice',
    },
    async execute(interaction) {
        try {
            const server = interaction.client.servers.get(interaction.guild.id);
            const voice = [...server.privateVoiceChannels.values()].find(v => v.creator.id === interaction.user.id);
            if (!voice) return interaction.reply({ content: 'You do not have a voice channel.', ephemeral: true });
            const target = interaction.options.getMember('user');
            if (await voice.removeMember(target)) {
                await interaction.reply({ content: `Removed ${target.user.tag} from your voice channel.`, ephemeral: true });
            } else {
                await interaction.reply({ content: `Failed to remove ${target.user.tag} from your voice channel.`, ephemeral: true });
            }
        } catch (err) {
            console.log(err);
        }
    },
};