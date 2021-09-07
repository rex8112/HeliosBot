module.exports = {
    name: 'channelDelete',
    async execute(channel) {
        if (channel.type === 'DM') return;
        const server = channel.client.servers.get(channel.guild.id);
        server.getPrivateCategory();
        server.save();
    },
};