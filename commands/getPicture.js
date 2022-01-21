const { SlashCommandBuilder } = require('@discordjs/builders');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('getpfp')
        .setDescription('Get the profile picture of a member')
        .addUserOption(option =>
            option
                .setName('member')
                .setDescription('The member to get the picture of')
                .setRequired(true)),
    async execute(interaction) {
        const member = interaction.options.getMember('member', true);

        return interaction.reply({
            content: `Link: ${member.displayAvatarURL()}`,
        });
    },
};