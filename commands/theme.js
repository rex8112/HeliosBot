const { SlashCommandBuilder } = require('@discordjs/builders');
const { Permissions, MessageEmbed } = require('discord.js');
const { roleMention } = require('@discordjs/builders');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('theme')
        .setDescription('Changes the theme of the guild.'),
    async execute(interaction) {
        const filter = m => m.author.id === interaction.user.id;
        if (!interaction.member.permissions.has([Permissions.FLAGS.MANAGE_GUILD, Permissions.FLAGS.MANAGE_ROLES])) {
            return interaction.reply({ content: 'You do not have permission to change the theme.', ephemeral: true });
        }
        const server = interaction.client.servers.get(interaction.guild.id);
        const embed = new MessageEmbed()
            .setColor('ORANGE')
            .setTitle('New Theme')
            .setDescription('Please enter the name of the new theme.');
        const data = new Map();

        const message = await interaction.reply({ embeds: [embed], fetchReply: true });
        const messages = await interaction.channel.awaitMessages({ filter, max: 1, time: 30000 });
        const themeName = messages.first().content;
        data.set('name', themeName);

        embed.setDescription('Please enter the new guild name.');
        await message.edit({ embeds: [embed] });
        const messages2 = await interaction.channel.awaitMessages({ filter, max: 1, time: 30000 });
        const guildName = messages2.first().content;
        data.set('guildName', guildName);
        const ranks = new Map();

        for (const rank of server.theme.ranks.values()) {
            const rankData = new Map();

            embed.setDescription(`Please enter the new name for: ${roleMention(rank.role.id)}`);
            await message.edit({ embeds: [embed] });
            const messages3 = await interaction.channel.awaitMessages({ filter, max: 1, time: 30000 });
            rankData.set('name', messages3.first().content);

            embed.setDescription(`Please enter the new max for ${roleMention(rank.role.id)}: \`${rank.maxMembers}\``);
            await message.edit({ embeds: [embed] });
            const messages4 = await interaction.channel.awaitMessages({ filter, max: 1, time: 30000 });
            const num = Number(messages4.first().content);
            if (isNaN(num)) continue;
            rankData.set('max', num);
            rankData.set('id', rank.role.id);
            ranks.set(rank.role.id, rankData);
        }
        data.set('ranks', ranks);
        embed.setDescription('All Done!');
        await message.edit({ embeds: [embed] });

        const { theme } = server;
        theme.name = data.get('name');
        theme.setGuildName(data.get('guildName'));
        for (const rank of data.get('ranks').values()) {
            theme.setRank(rank.get('id'), rank.get('name'), rank.get('max'));
        }
    },
};