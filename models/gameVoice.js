const { TextChannel, VoiceChannel, Collection, MessageEmbed, MessageActionRow, MessageButton } = require('discord.js');

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

        this.muteRole = this.guild.roles.cache.find(role => role.name === 'VoiceControlled');

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
        return this.team1Channel && this.team2Channel;
    }
    /**
     * Create the game message
     * @param {TextChannel} channel Channel to send the message to
     */
    async create(channel) {
        if (!this.muteRole) {
            await this.createRole();
        }
        this.message = await channel.send(`${this.name} is starting!`);
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
    async getEmbed() {
        const embeds = [];
        const embed = new MessageEmbed()
            .setTitle(`${this.name}`)
            .setColor('#0099ff')
            .setDescription(`Players: ${this.players.size}/${this.max}`)
            .addField('Game Type', `Teams: ${this.isTeams}\nMute: ${this.mute}\nDeaf: ${this.deaf}`);
        if (this.isTeams) {
            const t1String = this.team1.size > 0 ? this.team1.map(player => player.member.displayName).join(', ') : 'None';
            const t2String = this.team2.size > 0 ? this.team2.map(player => player.member.displayName).join(', ') : 'None';
            embed.addField('Team 1', `${this.team1Channel}\n${t1String}`);
            embed.addField('Team 2', `${this.team2Channel}\n${t2String}`);
        } else {
            embed.addField('Players', this.players.map(p => p.member.displayName).join('\n'));
        }
        embeds.push(embed);
        return embeds;
    }

    async getComponents() {
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
                    .setStyle('DANGER')
                    .setDisabled(!this.running),
            );
        if (this.allowDead) {
            row.addComponents(
                new MessageButton()
                    .setCustomId('gameDie')
                    .setLabel('Died')
                    .setStyle('SECONDARY')
                    .setDisabled(!this.running),
            );
        }
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

    // Game Commands
    async start() {
        for (const player of this.players.values()) {
            player.update(this.mute, this.deaf);

            // Move to team channel if they are in one
            if (this.team1Channel && this.team2Channel) {
                if (this.team1.findKey(player.id)) {
                    await player.member.voice.setChannel(this.team1Channel);
                } else {
                    await player.member.voice.setChannel(this.team2Channel);
                }
            }
        }
        this.running = true;
    }

    async end() {
        for (const player of this.players.values()) {
            player.update(false, false);
            // Move all players back to the lobby
            if (player.member.voice.channelId !== this.team1Channel.id) {
                await player.member.voice.setChannel(this.team1Channel);
            }
        }
        this.running = false;
    }

    async close() {
        for (const player of this.players.values()) {
            this.removeMember(player.member);
        }
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
            return;
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
    }

    async removeMember(member) {
        const player = this.players.get(member.id);
        if (player) {
            player.unmute();
            player.undeafen();
            player.update();
        }
        this.players.delete(member.id);
        if (this.isTeams) {
            // Clear their previous team
            if (this.team1.has(player.id)) {
                this.team1.delete(player.id);
            } else if (this.team2.has(player.id)) {
                this.team2.delete(player.id);
            }
        }
        await member.roles.remove(this.muteRole);
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
        await this.member.edit({ mute: mute, deaf: deafen });
    }

    async clear() {
        await this.member.edit({ mute: false, deaf: false });
    }
}