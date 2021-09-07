module.exports = {
    name: 'channelUpdate',
    async execute(oldchannel, channel) {
        if (channel.type === 'DM') return;
        const server = channel.client.servers.get(channel.guild.id);
        server.getPrivateCategory();
        server.save();
    },
};