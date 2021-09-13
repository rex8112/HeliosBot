const { SlashCommandBuilder } = require('@discordjs/builders');
const { MessageEmbed } = require('discord.js');
const { COLOR } = require('../models/colors');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('points')
        .setDescription('Gets your current points!'),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guild.id);
        const deck = server.getDeck(interaction.member);
        const embed = new MessageEmbed()
            .setColor(COLOR.points)
            .setTitle(`${interaction.member.displayName}'s Points`)
            .setDescription(`You have:\n**${deck.points.toLocaleString()}** Total Points\n\n**${deck.earnedPoints.toLocaleString()}** Activity Points`);

        return interaction.reply({ embeds: [embed], ephemeral: true });
    },
};