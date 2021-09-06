const { channelMention } = require('@discordjs/builders');
const { SlashCommandBuilder } = require('@discordjs/builders');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('topic')
        .setDescription('Create a new topic!')
        .addStringOption(option =>
            option.setName('name')
                .setDescription('The name of the topic, do not include "_n_shit"')
                .setRequired(true)),
    async execute(interaction) {
        const server = interaction.client.servers.get(interaction.guildId);
        if (!server.topicCategory) return interaction.reply({ content: 'No topic category set!', ephemeral: true });
        const name = interaction.options.getString('name');
        const description = `Discussion related to ${name}`;
        const topic = await server.newTopicChannel(name, description, interaction.member);
        await interaction.reply({ content: `Topic Created: ${channelMention(topic.channel.id)}`, ephemeral: true });
    },
};