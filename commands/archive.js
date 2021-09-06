const { SlashCommandBuilder } = require('@discordjs/builders');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('archive')
        .setDescription('Either show or hide the archive category')
        .addStringOption(option =>
            option
                .setName('option')
                .setDescription('Whether to show/hide the archive category.')
                .setRequired(true)
                .addChoice('Show', 'show')
                .addChoice('Hide', 'hide')),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        if (!server.archiveCategory) return interaction.reply({ content: 'There is no archive category.', ephemeral: true });
        if (interaction.options.getString('option') === 'show') {
            if (await server.showArchive(interaction.member)) {
                interaction.reply({ content: 'The archive category has been shown.', ephemeral: true });
            } else {
                interaction.reply({ content: 'The archive category does not exist.', ephemeral: true });
            }
        } else if (interaction.options.getString('option') === 'hide') {
            if (await server.hideArchive(interaction.member)) {
                interaction.reply({ content: 'The archive category has been hidden.', ephemeral: true });
            } else {
                interaction.reply({ content: 'The archive category does not exist.', ephemeral: true });
            }
        }
    },
};