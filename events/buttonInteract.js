const { MessageActionRow } = require('discord.js');

module.exports = {
    name: 'interactionCreate',
    async execute(interaction) {
        if (!interaction.isButton()) return;

        if (interaction.customId == 'saveTopic') {
            const server = interaction.client.servers.get(interaction.guild.id);
            const topic = server.topics.get(interaction.channelId);
            if (topic && (topic.archived || topic.pendingRemovalDate)) {
                await topic.unarchive(interaction.member);
            }
            const button = interaction.component;
            button.setDisabled(true);
            const row = new MessageActionRow().addComponents(button);
            await interaction.update({ components: [row] });
        }
    },
};