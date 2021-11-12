const { TextChannel, Collection } = require('discord.js');

class GameVoice {
    /**
     * Manage players ability to talk while in game
     * @param {*} server Server that the game is in
     * @param {string} name Name of the game session
     * @param {number} max Maximum amount of players
     * @param {bool} mute Whether to mute players or just deafen them
     * @param {bool} allowDead Whether to allow dead players to talk
     */
    constructor(server, name, max, mute, allowDead) {
        this.server = server;
        this.guild = server.guild;
        this.name = name;
        this.max = max;
        this.mute = mute;
        this.allowDead = allowDead;

        this.muteRole = this.guild.roles.cache.find(role => role.name === 'VoiceControlled');

        this.message = null;
        this.invite = null;
        this.players = new Collection();
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

    async createRole() {
        this.muteRole = this.guild.roles.cache.find(role => role.name === 'VoiceControlled');
        if (!this.muteRole) {
            this.muteRole = await this.guild.roles.create({
                name: 'VoiceControlled',
                reason: 'Did not exist before',
            });
        }
    }

    // Game Commands
    async start() {
        for (const player of this.players.values()) {
            player.deafen();
            if (this.mute) {
                player.mute();
            }
            player.update();
        }
    }

    async end() {
        for (const player of this.players.values()) {
            player.unmute();
            player.undeafen();
            player.update();
        }
    }

    async die(member) {
        const player = this.players.get(member.id);
        if (player) {
            player.unmute();
            player.undeafen();
            player.update();
        }
    }

    // Player Management
    async addMember(member) {
        if (this.players.size >= this.max) {
            return;
        }
        const player = new Player(member);
        this.players.set(member.id, player);
        await member.roles.add(this.muteRole);
    }

    async removeMember(member) {
        const player = this.players.get(member.id);
        if (player) {
            player.unmute();
            player.undeafen();
            player.update();
        }
        this.players.delete(member.id);
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

    mute() {
        this.muted = true;
    }

    unmute() {
        this.muted = false;
    }

    deafen() {
        this.deafened = true;
    }

    undeafen() {
        this.deafened = false;
    }

    async update() {
        await this.member.edit({ mute: this.muted, deaf: this.deafened });
    }

    async clear() {
        await this.member.edit({ mute: false, deaf: false });
    }
}