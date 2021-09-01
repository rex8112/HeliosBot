const fs = require('fs');
const { Client, Collection, Intents } = require('discord.js');
const { token } = require('./config.json');
const { Server } = require('./models/server');

const client = new Client({ intents: [Intents.FLAGS.GUILDS, Intents.FLAGS.GUILD_MESSAGES, Intents.FLAGS.GUILD_VOICE_STATES, Intents.FLAGS.GUILD_MEMBERS] });

client.commands = new Collection();
client.servers = new Collection();
const commandFiles = fs.readdirSync('./commands').filter(file => file.endsWith('.js'));
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

client.on('interactionCreate', async interaction => {
    if (!interaction.isCommand()) return;

    const command = client.commands.get(interaction.commandName);

    if (!command) return;

    try {
        await command.execute(interaction);
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

client.login(token);
