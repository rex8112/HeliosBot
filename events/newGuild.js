const { Server } = require('../models/server.js');

module.exports = {
    name: 'guildCreate',
    once: true,
    async execute(guild) {
        const client = guild.client;
        const server = await new Server(client, guild).load();
        client.servers.set(guild.id, server);
    },
};