const { default: Collection } = require('@discordjs/collection');
const { VoiceLast } = require('../models/voice');

module.exports = {
    name: 'voiceStateUpdate',
    async execute(oldState, newState) {
        try {
            if (newState.channel?.name !== 'Create Channel') return;
            const server = newState.guild.client.servers.get(newState.guild.id);
            const privateCreator = server.privateVoiceChannelCreator;
            if (!privateCreator) return;
            const existing = server.privateVoiceChannels.find(c => c.creator.id === newState.member.id);
            if (existing) {
                await newState.setChannel(existing.voiceChannel, 'Already existing Voice Channel');
                return;
            }
            const voiceLast = await new VoiceLast(newState.member).load();
            let voice;
            if (voiceLast.name) {
                voice = await server.newVoiceChannel(voiceLast.name, newState.member, voiceLast.whitelist, false, voiceLast.members);
            } else {
                voice = await server.newVoiceChannel(`${newState.member.displayName}'s Channel`, newState.member, true, false, new Collection());
            }
            await newState.setChannel(voice.voiceChannel, 'Created Private Voice Channel');
        } catch (error) {
            console.error(error);
        }
    },
};