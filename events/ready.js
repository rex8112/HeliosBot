const { sequelize } = require('../tools/database.js');
const { Server } = require('../models/server.js');
const { default: Collection } = require('@discordjs/collection');

const wait = require('util').promisify(setTimeout);

module.exports = {
    name: 'ready',
    once: true,
    async execute(client) {
        console.log(`Ready! Logged in as ${client.user.tag}`);
        await sequelize.sync();
        console.log('Database synced');
        client.user.setActivity('/ commands', { type: 'LISTENING' });
        for (const guild of client.guilds.cache.values()) {
            const server = await new Server(client, guild).load();
            client.servers.set(guild.id, server);
        }
        console.log('Servers loaded');
        // Check if bot permissions need to be set
        const commands = await client.application.commands.fetch(undefined, { force: true });
        const commandPerms = new Collection();
        for (const command of commands.values()) {
            const commandData = client.commands.get(command.name);
            if (commandData) {
                const rolePermissions = commandData.rolePermissions;
                if (rolePermissions) {
                    commandPerms.set(command.id, rolePermissions);
                }
            }
        }

        for (const server of client.servers.values()) {
            await server.setCommandsPermissions(commandPerms);
        }
        console.log('Permissions set');
    },
};