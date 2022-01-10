const { SlashCommandBuilder, time } = require('@discordjs/builders');
const { MessageEmbed, MessageActionRow, MessageButton, Collection } = require('discord.js');
const { TTK } = require('../tools/database');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('ttk')
        .setDescription('Tarkov Team Kills')
        .addSubcommand(subcommand =>
            subcommand
                .setName('report')
                .setDescription('Report a team kill')
                .addUserOption(option =>
                    option.setName('killer')
                        .setDescription('The user who killed the victim.')
                        .setRequired(true))
                .addUserOption(option =>
                    option.setName('victim')
                        .setDescription('The user who was killed. This defaults to you.'))
                .addStringOption(option =>
                    option.setName('notes')
                        .setDescription('Any notes you want to add.')))
        .addSubcommand(subcommand =>
            subcommand
                .setName('query')
                .setDescription('Get a user\'s team kills')
                .addUserOption(option =>
                    option.setName('user')
                        .setDescription('The user to get the team kills of.')
                        .setRequired(true)))
        .addSubcommand(subcommand =>
            subcommand
                .setName('queryindex')
                .setDescription('Get a team kill by index')
                .addNumberOption(option =>
                    option.setName('index')
                        .setDescription('The index of the team kill to get.')
                        .setRequired(true))),
    async execute(interaction) {
        if (interaction.options.getSubcommand() === 'report') {
            const server = interaction.client.servers.get(interaction.guild.id);
            const killer = interaction.options.getMember('killer', true);
            const victim = interaction.options.getMember('victim') ?? interaction.member;
            const reporter = interaction.member;
            const notes = interaction.options.getString('notes');
            if (killer.id === victim.id) {
                return interaction.reply({ content: 'You cannot Team Kill yourself, you are just bad.', ephemeral: true });
            }
            let message = await interaction.deferReply();
            let entry;
            try {
                entry = await TTK.create({
                    killerId: killer.id,
                    killerUsername: `${killer.user.username}#${killer.user.discriminator}`,
                    victimId: victim.id,
                    victimUsername: `${victim.user.username}#${victim.user.discriminator}`,
                    reporterId: reporter.id,
                    reporterUsername: `${reporter.user.username}#${reporter.user.discriminator}`,
                    notes: notes,
                });
            } catch (error) {
                return interaction.editReply({ content: `Something went wrong reporting that kill.\n\n\`\`\`${error}\`\`\`` });
            }
            message = await interaction.editReply({
                content: `${reporter} Reported Kill \`${entry.index}\`: ${killer} Killed ${victim} ${time(entry.createdAt, 'R')}\n\n${notes ?? ''}`,
                components: getComponents(entry.index),
            });
            const votes = new tkVotes(entry.index, message);
            server.tkVotes.set(entry.index, votes);
        } else if (interaction.options.getSubcommand() === 'query') {
            const user = interaction.options.getMember('user', true);
            await interaction.deferReply();
            const kills = await TTK.findAll({
                where: {
                    killerId: user.id,
                },
                order: [['index', 'DESC']],
            });
            const deaths = await TTK.findAll({
                where: {
                    victimId: user.id,
                },
                order: [['index', 'DESC']],
            });
            let killString = kills.slice(0, 3).map(k => `\`${k.index}\` ${k.notes ? '\\*' : ''}Killed **${k.victimUsername}** on ${time(k.createdAt)}`).join('\n');
            let deathString = deaths.slice(0, 3).map(d => `\`${d.index}\` ${d.notes ? '\\*' : ''}Killed by **${d.killerUsername}** on ${time(d.createdAt)}`).join('\n');
            if (killString.length === 0) killString = 'No kills.';
            if (deathString.length === 0) deathString = 'No deaths.';
            const embed = new MessageEmbed()
                .setTitle(`${user.displayName}'s TK Report`)
                .setColor('DARK_RED')
                .addField('Stats', `Kills: ${kills.length}\nDeaths: ${deaths.length}`, true)
                .addField('Last Kills', `${killString}`)
                .addField('Last Deaths', `${deathString}`)
                .setFooter('* There is a note attached to this kill.');
            return interaction.editReply({ content: null, embeds: [embed] });
        } else if (interaction.options.getSubcommand() === 'queryindex') {
            const index = interaction.options.getNumber('index', true);
            await interaction.deferReply();
            const kill = await TTK.findOne({
                where: {
                    index,
                },
            });
            if (!kill) return interaction.editReply({ content: 'That kill does not exist.' });

            let killer;
            let victim;
            let reporter;
            try {
                killer = await interaction.guild.members.fetch(kill.killerId);
            } catch (error) {
                killer = kill.killerUsername;
            }
            try {
                victim = await interaction.guild.members.fetch(kill.victimId);
            } catch (error) {
                victim = kill.victimUsername;
            }
            try {
                reporter = await interaction.guild.members.fetch(kill.reporterId);
            } catch (error) {
                reporter = kill.reporterUsername;
            }
            const embed = new MessageEmbed()
                .setTitle(`Kill #${kill.index}`)
                .setColor('DARK_RED')
                .setDescription(`${kill.justified ? '***Justified***\n' : ''}**${killer ?? kill.killerUsername}** killed **${victim ?? kill.victimUsername}** on ${time(kill.createdAt)}\n\nReported by **${reporter}**`);
            if (kill.notes) embed.addField('Notes', kill.notes);
            return interaction.editReply({ content: null, embeds: [embed] });
        }
    },
};

function getComponents(index) {
    const components = [];
    const row = new MessageActionRow()
        .addComponents(
            new MessageButton()
                .setCustomId(`ttkJustified-${index}`)
                .setLabel('Justified')
                .setStyle('SUCCESS'),
            new MessageButton()
                .setCustomId(`ttkUnjustified-${index}`)
                .setLabel('Unjustified')
                .setStyle('DANGER'),
        );
    components.push(row);
    return components;
}

class tkVotes {
    constructor(server, index, message) {
        this.server = server;
        this.index = index;
        this.message = message;
        this.votes = new Collection();
        setTimeout(() => this.finishVoting(), 600000);
    }

    get yes() {
        return this.votes.filter(v => v === true).size;
    }

    get no() {
        return this.votes.filter(v => v === false).size;
    }

    addVote(user, vote) {
        this.votes.set(user.id, vote);
        return true;
    }

    async finishVoting() {
        await TTK.update({
            justified: this.isJustified(),
        }, {
            where: {
                index: this.index,
            },
        });
        await this.message.edit({
            components: [],
            content: `${this.message.content}\n\n${this.isJustified() ? 'The kill was justified.' : 'The kill was not justified.'}`,
        });
        this.server.tkVotes.delete(this.index);
    }

    isJustified() {
        return this.yes > this.no;
    }
}