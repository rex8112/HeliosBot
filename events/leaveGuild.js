module.exports = {
    name: 'guildDelete',
    once: true,
    async execute(guild) {
        const client = guild.client;
        client.servers.delete(guild.id);
    },
};