const { MessageActionRow } = require('discord.js');

module.exports = {
    name: 'interactionCreate',
    async execute(interaction) {
        if (!interaction.isButton() && !interaction.isSelectMenu()) return;

        if (interaction.customId.startsWith('game')) {
            const game = interaction.client.servers.get(interaction.guild.id)?.getGame(interaction.message.id);
            if (!game) return interaction.reply({ content: 'Game is no longer active.', ephemeral: true });
            return game.handleInteraction(interaction);
        }
    },
};