const { sequelize } = require('../tools/database.js');
const { Server } = require('../models/server.js');

module.exports = {
    name: 'ready',
    once: true,
    async execute(client) {
        console.log(`Ready! Logged in as ${client.user.tag}`);
        await sequelize.sync();
        console.log('Database synced');
        for (const guild of client.guilds.cache.values()) {
            const server = await new Server(client, guild).load();
            client.servers.set(guild.id, server);
        }
    },
};