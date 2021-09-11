const fs = require('fs');
const { Client, Collection, Intents } = require('discord.js');
const { token } = require('./config.json');
const { Server } = require('./models/server');

const client = new Client({ intents: [Intents.FLAGS.GUILDS, Intents.FLAGS.GUILD_MESSAGES, Intents.FLAGS.GUILD_VOICE_STATES, Intents.FLAGS.GUILD_MEMBERS] });

client.commands = new Collection();
client.contexts = new Collection();
client.servers = new Collection();
const commandFiles = fs.readdirSync('./commands').filter(file => file.endsWith('.js'));
const contextFiles = fs.readdirSync('./contexts').filter(file => file.endsWith('.js'));
const eventFiles = fs.readdirSync('./events').filter(file => file.endsWith('.js'));

for (const file of eventFiles) {
    const event = require(`./events/${file}`);
    if (event.once) {
        client.once(event.name, (...args) => event.execute(...args));
    } else {
        client.on(event.name, (...args) => event.execute(...args));
    }
}

for (const file of commandFiles) {
    const command = require(`./commands/${file}`);
    client.commands.set(command.data.name, command);
}

for (const file of contextFiles) {
    const context = require(`./contexts/${file}`);
    client.contexts.set(context.data.name, context);
}

client.on('interactionCreate', async interaction => {
    if (!interaction.isCommand()) return;

    const command = client.commands.get(interaction.commandName);

    if (!command) return;

    try {
        await command.execute(interaction);
    } catch (error) {
        console.error(error);
        try {
            await interaction.reply({ content: 'There was an error while executing this command!', ephemeral: true });
        } catch (e) {
            console.error(e);
            await interaction.channel.send({ content: 'There was an error while executing this command!', ephemeral: true });
        }
    }
});

client.on('interactionCreate', async interaction => {
    if (!interaction.isContextMenu()) return;

    const context = client.contexts.get(interaction.commandName);

    if (!context) return;

    try {
        await context.execute(interaction);
    } catch (error) {
        console.error(error);
        await interaction.reply({ content: 'There was an error while executing this command!', ephemeral: true });
    }
});

setInterval(() => {
    try {
        for (const server of client.servers.values()) {
            server.checkTopicChannels();
            server.checkCompetitiveRanking();
        }
    } catch (error) {
        console.error(error);
    }
}, 1 * 60 * 1000);

setInterval(() => {
    try {
        for (const server of client.servers.values()) {
            server.checkVoiceChannels(Server.POINTS_PER_MINUTE * 2);
        }
    } catch (error) {
        console.error(error);
    }
}, 2 * 60 * 1000);

setInterval(() => {
    try {
        for (const server of client.servers.values()) {
            server.checkPrivateVoiceChannels();
        }
    } catch (error) {
        console.error(error);
    }
}, 10 * 1000);

client.login(token);
