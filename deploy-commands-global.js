const fs = require('fs');
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v9');
const { clientId, token } = require('./config.json');

const commands = [];
const contexts = [];
const commandFiles = fs.readdirSync('./commands').filter(file => file.endsWith('.js'));
const contextFiles = fs.readdirSync('./contexts').filter(file => file.endsWith('.js'));

for (const file of commandFiles) {
    const command = require(`./commands/${file}`);
    commands.push(command.data.toJSON());
}
for (const file of contextFiles) {
    const context = require(`./contexts/${file}`);
    contexts.push(context.data);
}

const rest = new REST({ version: '9' }).setToken(token);

(async () => {
    try {
        await rest.put(
            Routes.applicationCommands(clientId),
            { body: commands.concat(contexts) },
        );

        console.log('Successfully registered application commands.');
    } catch (error) {
        console.error(error);
    }
})();
