const { TextChannel, VoiceChannel, Collection, MessageEmbed, MessageActionRow, MessageButton, ButtonInteraction } = require('discord.js');

class GameVoice {
    /**
     * Manage players ability to talk while in game
     * @param {*} server Server that the game is in
     * @param {string} name Name of the game session
     * @param {number} max Maximum amount of players
     * @param {bool} mute Whether to mute players or just deafen them
     * @param {bool} allowDead Whether to allow dead players to talk
     */
    constructor(server, name, max, mute, deaf, allowDead) {
        this.server = server;
        this.guild = server.guild;
        this.name = name;
        this.max = max;
        this.mute = mute;
        this.deaf = deaf;
        this.allowDead = allowDead;

        this.muteRole = server.muteRole;

        this.running = false;
        this.message = null;
        this.team1Channel = null;
        this.team2Channel = null;
        this.invite = null;
        this.privateInvite = false;

        this.players = new Collection();
        this.team1 = new Collection();
        this.team2 = new Collection();
    }

    // Properties
    get isTeams() {
        return this.team1Channel != null && this.team2Channel != null;
    }

    get id() {
        return this.message?.id || null;
    }

    get host() {
        return this.players.first();
    }
    /**
     * Create the game message
     * @param {TextChannel} channel Channel to send the message to
     */
    async build(channel) {
        if (!this.muteRole) {
            await this.createRole();
        }
        this.message = await channel.send({ embeds: this.getEmbeds(), components: this.getComponents() });
    }

    /**
     * Create the mute role
     */
    async createRole() {
        this.muteRole = this.guild.roles.cache.find(role => role.name === 'VoiceControlled');
        if (!this.muteRole) {
            this.muteRole = await this.guild.roles.create({
                name: 'VoiceControlled',
                reason: 'Did not exist before',
            });
        }
    }

    /**
     * Set the team channels
     * @param {VoiceChannel} team1
     * @param {VoiceChannel} team2
     */
    async setTeams(team1, team2) {
        this.team1Channel = team1;
        this.team2Channel = team2;
    }

    /**
     * Set the invite for the game
     * @param {string} invite The invite link or code to join the game
     * @param {bool} priv Whether the invite is private or not
     */
    async setInvite(invite, priv = false) {
        this.invite = invite;
        this.privateInvite = priv;
    }

    // Embed Management
    getEmbeds() {
        let desc = `Game Host: ${this.host?.member}\nPlayers: ${this.players.size}/${this.max}`;
        if (this.invite) {
            desc += `\nInvite: ${this.privateInvite ? 'Private' : this.invite}`;
        }
        const embeds = [];
        const embed = new MessageEmbed()
            .setTitle(`${this.name}`)
            .setColor('#0099ff')
            .setDescription(desc)
            .addField('Game Type', `Teams: ${this.isTeams ? 'True' : 'False'}\nMute: ${this.mute}\nDeaf: ${this.deaf}`);
        if (this.isTeams) {
            const t1String = this.team1.size > 0 ? this.team1.map(player => player.member.displayName).join('\n') : 'None';
            const t2String = this.team2.size > 0 ? this.team2.map(player => player.member.displayName).join('\n') : 'None';
            embed.addField('Team 1', `${this.team1Channel}\n${t1String}`);
            embed.addField('Team 2', `${this.team2Channel}\n${t2String}`);
        } else {
            const pString = this.players.map(p => p.member.displayName).join('\n');
            embed.addField('Players', pString ? pString : 'None');
        }
        embeds.push(embed);
        return embeds;
    }

    getComponents() {
        const components = [];
        const row = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('gameStart')
                    .setLabel('Start')
                    .setStyle('SUCCESS')
                    .setDisabled(!this.players.size || this.running),
                new MessageButton()
                    .setCustomId('gameEnd')
                    .setLabel('End')
                    .setStyle('SECONDARY')
                    .setDisabled(!this.running),
            );
        if (this.allowDead) {
            row.addComponents(
                new MessageButton()
                    .setCustomId('gameDie')
                    .setLabel('Died')
                    .setStyle('DANGER')
                    .setDisabled(!this.running),
            );
        }
        row.addComponents(
            new MessageButton()
                .setCustomId('gameClose')
                .setLabel('Close')
                .setStyle('SECONDARY')
                .setDisabled(this.running),
        );
        components.push(row);

        const row2 = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('gameJoin')
                    .setLabel('Join')
                    .setStyle('PRIMARY'),
                new MessageButton()
                    .setCustomId('gameLeave')
                    .setLabel('Leave')
                    .setStyle('SECONDARY'),
            );
        const row2t = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('gameJoin1')
                    .setLabel('Join Team 1')
                    .setStyle('PRIMARY'),
                new MessageButton()
                    .setCustomId('gameJoin2')
                    .setLabel('Join Team 2')
                    .setStyle('PRIMARY'),
                new MessageButton()
                    .setCustomId('gameLeave')
                    .setLabel('Leave')
                    .setStyle('SECONDARY'),
            );
        if (this.isTeams) {
            components.push(row2t);
        } else {
            components.push(row2);
        }

        return components;
    }

    async updateMessage(interaction = null) {
        if (interaction && !interaction.deffered) {
            return interaction.update({ embeds: this.getEmbeds(), components: this.getComponents() });
        } else {
            return this.message.edit({ embeds: this.getEmbeds(), components: this.getComponents() });
        }
    }

    /**
     * Handle discord interaction with the game
     * @param {ButtonInteraction} interaction Discord interaction
     */
    async handleInteraction(interaction) {
        const customId = interaction.customId;
        if (customId === 'gameDie') {
            await this.die(interaction.member);
            return interaction.reply({ content: 'You have died.', ephemeral: true });
        } else if (customId === 'gameJoin') {
            if (!interaction.member.voice.channel) {
                return interaction.reply({ content: 'You must be in a voice channel to join.', ephemeral: true });
            }
            const result = await this.addMember(interaction.member);
            if (result) {
                if (this.privateInvite) {
                    this.updateMessage();
                    return interaction.reply({ content: `Invite: ${this.invite}`, ephemeral: true });
                } else {
                    return this.updateMessage(interaction);
                }
            } else {
                return interaction.reply({ content: 'Maximum Players reached!', ephemeral: true });
            }
        } else if (customId === 'gameLeave') {
            await this.removeMember(interaction.member);
            return this.updateMessage(interaction);
        } else if (customId === 'gameJoin1') {
            const result = await this.addMember(interaction.member, 1);
            if (result) {
                return this.updateMessage(interaction);
            } else {
                return interaction.reply({ content: 'Maximum Players reached!', ephemeral: true });
            }
        } else if (customId === 'gameJoin2') {
            const result = await this.addMember(interaction.member, 2);
            if (result) {
                return this.updateMessage(interaction);
            } else {
                return interaction.reply({ content: 'Maximum Players reached!', ephemeral: true });
            }
        }
        if (interaction.member.id === this.host?.id) {
            if (customId === 'gameStart') {
                await interaction.deferUpdate();
                await this.start();
                return this.updateMessage(interaction);
            } else if (customId === 'gameEnd') {
                await interaction.deferUpdate();
                await this.end();
                return this.updateMessage(interaction);
            } else if (customId === 'gameClose') {
                await this.close();
                return interaction.reply({ content: 'Game closed.', ephemeral: true });
            }
        } else {
            return interaction.reply({ content: 'You are not the host.', ephemeral: true });
        }
    }

    // Game Commands
    async start() {
        for (const player of this.players.values()) {
            player.update(this.mute, this.deaf);

            // Move to team channel if they are in one
            if (this.team1Channel && this.team2Channel) {
                if (this.team1.get(player.id)) {
                    await player.setChannel(this.team1Channel);
                } else {
                    await player.setChannel(this.team2Channel);
                }
            }
        }
        this.running = true;
    }

    async end() {
        for (const player of this.players.values()) {
            player.update(false, false);
            // Move all players back to the lobby
            if (this.isTeams) {
                if (player.member.voice.channelId !== this.team1Channel?.id) {
                    await player.setChannel(this.team1Channel);
                }
            }
        }
        this.running = false;
    }

    async close() {
        for (const player of this.players.values()) {
            this.removeMember(player.member);
        }
        this.server.games.delete(this.id);
        const embed = this.message.embeds[0];
        embed.setColor('RED');
        embed.setFooter('Game Closed');
        await this.message.edit({ embeds: [embed], components: [] });
    }

    async die(member) {
        const player = this.players.get(member.id);
        if (player) {
            player.update(false, false);
        }
    }

    // Player Management
    async addMember(member, team = 0) {
        if (this.players.size >= this.max) {
            return false;
        }
        const player = new Player(member);
        this.players.set(member.id, player);
        await member.roles.add(this.muteRole);

        // Set the team
        if (this.isTeams) {
            // Clear their previous team
            if (this.team1.has(player.id)) {
                this.team1.delete(player.id);
            } else if (this.team2.has(player.id)) {
                this.team2.delete(player.id);
            }
            // Set their new team
            if (team === 1) {
                this.team1.set(member.id, player);
            } else if (team === 2) {
                this.team2.set(member.id, player);
            }
        }
        return true;
    }

    async removeMember(member) {
        const player = this.players.get(member.id);
        let result;
        if (player) {
            result = player.update(false, false);
            this.players.delete(member.id);
            if (this.isTeams) {
                // Clear their previous team
                if (this.team1.has(player.id)) {
                    this.team1.delete(player.id);
                } else if (this.team2.has(player.id)) {
                    this.team2.delete(player.id);
                }
            }
        }
        if (result) {
            await member.roles.remove(this.muteRole);
        }
    }
}

class Player {
    constructor(member) {
        this.member = member;
        this.id = member.id;

        this.muted = member.voice.mute;
        this.deafened = member.voice.deaf;
    }

    /**
     * Set the player's voice state
     * @param {bool} mute Set the mute status
     * @param {bool} deafen Set the deafen status
     */
    async update(mute, deafen) {
        this.muted = mute;
        this.deafened = deafen;
        try {
            await this.member.edit({ mute: mute, deaf: deafen });
            return true;
        } catch (e) {
            return false;
        }
    }

    async setChannel(channel) {
        try {
            await this.member.voice.setChannel(channel);
            return true;
        } catch (e) {
            return false;
        }
    }

    async clear() {
        await this.update(false, false);
    }
}

module.exports = {
    GameVoice,
    Player,
};