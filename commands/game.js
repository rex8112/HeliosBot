const { SlashCommandBuilder } = require('@discordjs/builders');
const { Permissions } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('game')
        .setDescription('Create a voice controller for a game.')
        .addSubcommand(subcommand =>
            subcommand
                .setName('ingame')
                .setDescription('Manages muting and deafening to enforce in game VC.')
                .addStringOption(option =>
                    option
                        .setName('name')
                        .setDescription('The name of the game.')
                        .setRequired(true))
                .addNumberOption(option =>
                    option
                        .setName('maxplayers')
                        .setDescription('The maximum number of players.')
                        .setRequired(true))
                .addBooleanOption(option =>
                    option
                        .setName('mute')
                        .setDescription('Whether or not to mute players during the game.')
                        .setRequired(true))
                .addBooleanOption(option =>
                    option
                        .setName('deafen')
                        .setDescription('Whether or not to deafen players during the game. Players can still talk.')
                        .setRequired(true))
                .addBooleanOption(option =>
                    option
                        .setName('allowdead')
                        .setDescription('Whether or not to allow dead players to talk during the game.')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('teams')
                .setDescription('Manages splitting teams up into their own VC and returning at the end.')
                .addStringOption(option =>
                    option
                        .setName('name')
                        .setDescription('The name of the game.')
                        .setRequired(true))
                .addNumberOption(option =>
                    option
                        .setName('maxplayers')
                        .setDescription('The maximum number of players.')
                        .setRequired(true))
                .addChannelOption(option =>
                    option
                        .setName('team1')
                        .setDescription('The channel to put team 1 in.')
                        .setRequired(true))
                .addChannelOption(option =>
                    option
                        .setName('team2')
                        .setDescription('The channel to put team 2 in.')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('fixme')
                .setDescription('Use this in case you get stuck muted/deafened from the bot.')),
    async execute(interaction) {
        const options = interaction.options;
        const subcommand = options.getSubcommand();
        const server = interaction.client.servers.get(interaction.guild.id);
        const name = options.getString('name');
        const maxplayers = options.getNumber('maxplayers');
        let game;

        if (subcommand === 'ingame') {
            const mute = options.getBoolean('mute');
            const deafen = options.getBoolean('deafen');
            const allowdead = options.getBoolean('allowdead');
            game = await server.newGame(interaction.channel, name, maxplayers, mute, deafen, allowdead);
        } else if (subcommand === 'teams') {
            const team1 = options.getChannel('team1');
            const team2 = options.getChannel('team2');
            game = await server.newGame(interaction.channel, name, maxplayers, false, false, false, team1, team2);
        } else if (subcommand === 'fixme') {
            const member = interaction.member;
            if (member.voiceState.channelId && member.roles.has(server.mutedRole)) {
                await member.edit({ mute: false, deafen: false });
                await member.roles.remove(server.mutedRole);
                return interaction.reply({ content: 'You have been fixed!', ephemeral: true });
            } else {
                return interaction.reply({ content: 'You need to be in a voice channel.', ephemeral: true });
            }
        }
        if (game) {
            return interaction.reply({ content: 'Game Created', ephemeral: true });
        } else {
            return interaction.reply({ content: 'Could not create game', ephemeral: true });
        }
    },
};