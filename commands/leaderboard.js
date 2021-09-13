const { SlashCommandBuilder, userMention, bold } = require('@discordjs/builders');
const { MessageEmbed } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('leaderboard')
        .setDescription('Replies with leaderboard of the server'),
    async execute(interaction) {
        if (!interaction.guild) {
            return interaction.reply('This command can only be used in a server');
        }
        await interaction.deferReply();
        const server = interaction.client.servers.get(interaction.guild.id);
        const ranks = server.theme.ranks;
        if (ranks.length === 0) {
            return interaction.reply({ content: 'No ranks are set up and I do not currently support the leaderboard without them.', ephemeral: true });
        }
        const embeds = [];
        let position = 1;
        for (const rank of ranks) {
            if (rank.isBotOnly()) continue;
            const decks = Array.from(rank.role.members.mapValues(member => server.getDeck(member)).values()).filter(deck => deck);
            decks.sort((a, b) => b.compareToDeck(a));
            let string = '';
            for (let i = 0; i < decks.length; i++) {
                let add = false;
                const deck = decks[i];
                let stringToAdd = `${position}. ${userMention(deck.member.id)}: ${deck.earnedPoints.toLocaleString()} Activity Points`;
                if (i < 5) add = true;
                if (deck.member.id === interaction.member.id) {
                    stringToAdd = bold(stringToAdd);
                    if (!add) {
                        stringToAdd = `...\n${stringToAdd}`;
                        add = true;
                    }
                } else if (i === decks.length - 1 && !add) {
                    stringToAdd = `...\n${stringToAdd}`;
                    add = true;
                }
                if (add) {
                    string += `${stringToAdd}\n`;
                }
                position++;
            }
            const embed = new MessageEmbed()
                .setColor(rank.role.color)
                .setTitle(rank.role.name)
                .setDescription(string);
            if (embeds.length < 10) {
                embeds.push(embed);
            }
        }
        await interaction.editReply({ embeds });
    },
};