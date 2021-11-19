const { VoiceLast } = require('../models/voice');

module.exports = {
    name: 'voiceStateUpdate',
    async execute(oldState, newState) {
        try {
            if (newState.name !== 'Create Channel') return;
            const server = newState.guild.client.servers.get(newState.guild.id);
            const privateCreator = server.privateVoiceChannelCreator;
            if (!privateCreator) return;
            const voiceLast = await new VoiceLast(newState.member).load();
            if (voiceLast.name) {
                const channel = await server.newVoiceChannel(voiceLast.name, newState.member, voiceLast.whitelist, false, voiceLast.members);
                await newState.setChannel(channel, 'Created Private Voice Channel');
            }
        } catch (error) {
            console.error(error);
        }
    },
};