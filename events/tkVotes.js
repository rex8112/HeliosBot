const { MessageActionRow } = require('discord.js');
const { TTK } = require('../tools/database');

module.exports = {
    name: 'interactionCreate',
    async execute(interaction) {
        if (!interaction.isButton()) return;

        if (interaction.customId.startsWith('ttkJustified')) {
            const index = parseInt(interaction.customId.split('-').pop());
            const server = interaction.client.servers.get(interaction.guild.id);
            if (!server) return interaction.reply({ content: 'The bot is still starting up.', ephemeral: true });
            const votes = server.tkVotes.get(index);
            if (!votes) return interaction.reply({ content: 'This vote has already been closed.', ephemeral: true });
            const voice = interaction.member.voice;
            if (!voice?.channelId) return interaction.reply({ content: 'You must be in a voice channel to vote.', ephemeral: true });
            votes.addVote(interaction.member, true);
            TTK.update({ justified: votes.isJustified() }, { where: { index: index } });
            return interaction.reply({ content: `You have voted the kill was justified.\n\nJustified: \`${votes.yes}\`\nUnjustified: \`${votes.no}\``, ephemeral: true });
        } else if (interaction.customId.startsWith('ttkUnjustified')) {
            const index = parseInt(interaction.customId.split('-').pop());
            const server = interaction.client.servers.get(interaction.guild.id);
            if (!server) return interaction.reply({ content: 'The bot is still starting up.', ephemeral: true });
            const votes = server.tkVotes.get(index);
            if (!votes) return interaction.reply({ content: 'This vote has already been closed.', ephemeral: true });
            const voice = interaction.member.voice;
            if (!voice?.channelId) return interaction.reply({ content: 'You must be in a voice channel to vote.', ephemeral: true });
            votes.addVote(interaction.member, false);
            TTK.update({ justified: votes.isJustified() }, { where: { index: index } });
            return interaction.reply({ content: `You have voted the kill was unjustified.\n\nJustified: \`${votes.yes}\`\nUnjustified: \`${votes.no}\``, ephemeral: true });
        }
    },
};