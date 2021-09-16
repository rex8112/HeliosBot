const { MessageActionRow } = require('discord.js');

module.exports = {
    name: 'interactionCreate',
    async execute(interaction) {
        if (!interaction.isButton()) return;

        if (interaction.customId.startsWith('casino')) {
            const casino = interaction.client.servers.get(interaction.guild.id).casino;
            casino.handleInteraction(interaction);
        }
    },
};