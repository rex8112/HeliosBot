const { Voice: VoiceDB, VoiceTemplate } = require('../tools/database');
const { GuildMember, MessageEmbed, Collection } = require('discord.js');
const { userMention } = require('@discordjs/builders');

class Voice {
    /**
     * @param {string} name
     * @param {GuildMember} member
     * @param {string} voiceChannelId
     * @param {string} textChannelId
     */
    constructor(server, voiceChannelId = null, textChannelId = null) {
        this.server = server;
        this.name = '';
        this.creator = null;
        this.guild = server.guild;
        this.voiceChannelId = voiceChannelId;
        this.textChannelId = textChannelId;
        this.whitelist = false;
        this.members = new Map();
        this.creationTimestamp = Number(Date.now());
        this.welcomeMessage = null;
        this.loaded = false;

        if (voiceChannelId) {
            this.voiceChannel = this.guild.channels.cache.get(voiceChannelId);
        } else {
            this.voiceChannel = null;
        }
        if (textChannelId) {
            this.textChannel = this.guild.channels.cache.get(textChannelId);
        } else {
            this.textChannel = null;
        }
    }

    static MINUTES = 10;

    toJSON() {
        return {
            creatorId: this.creator.id,
            voiceId: this.voiceChannelId,
            textId: this.textChannelId,
            whitelist: this.whitelist,
            welcomeId: this.welcomeMessage ? this.welcomeMessage.id : null,
            members: [...this.members.values()].map(m => m.id),
        };
    }

    async build(name, member, whitelist, nsfw = false) {
        this.name = name;
        this.creator = member;
        this.whitelist = whitelist;
        const data = await VoiceDB.findOne({ where: { creatorId: this.creator.id } });
        if (data) return false;
        const privateCategory = this.server.privateCategory;
        if (!privateCategory) return false;
        const permissions = [];
        if (whitelist) {
            this.members.set(this.guild.client.user.id, this.guild.client.user);
            this.members.set(member.id, member);
        }
        for (const id of this.members.keys()) {
            if (this.whitelist) {
                const allowPermission = Voice.getAllowPermission(id);
                permissions.push(allowPermission);
            } else {
                const denyPermission = Voice.getDenyPermission(id);
                permissions.push(denyPermission);
            }
        }
        // Set everyone permissions
        if (!this.whitelist) {
            const allowPermission = Voice.getAllowPermission(this.guild.roles.everyone.id, 'role');
            permissions.push(allowPermission);
        } else {
            const denyPermission = Voice.getDenyPermission(this.guild.roles.everyone.id, 'role');
            permissions.push(denyPermission);
        }

        // Create channels
        const voiceChannel = await this.guild.channels.create(this.name, {
            type: 'GUILD_VOICE',
            parent: privateCategory,
            permissionOverwrites: permissions,
            reason: `Created by ${this.creator.user.tag}`,
        });
        const textChannel = await this.guild.channels.create(this.name, {
            type: 'GUILD_TEXT',
            parent: privateCategory,
            permissionOverwrites: permissions,
            reason: `Created by ${this.creator.user.tag}`,
            nsfw: nsfw,
        });
        this.textChannel = textChannel;
        this.textChannelId = textChannel.id;
        this.voiceChannel = voiceChannel;
        this.voiceChannelId = voiceChannel.id;
        this.creationTimestamp = voiceChannel.createdTimestamp;
        this.loaded = true;

        // Send welcome message
        const memberString = [...this.members.keys()].map(id => userMention(id)).join('\n');
        const embed = new MessageEmbed()
            .setColor('GREEN')
            .setTitle(`${voiceChannel.name} Created Successfully`)
            .setDescription(`This channel will persist for ${Voice.MINUTES} minutes or until everyone is gone, whichever comes last.\nKeep in mind, Administrators can still see all of these channels.`)
            .addField('Creator', userMention(this.creator.id), true)
            .addField(`${this.whitelist ? 'Allowed' : 'Blocked'} People`, memberString ? memberString : 'None', true);
        this.welcomeMessage = await this.textChannel.send({ embeds: [embed] });
        await this.welcomeMessage.pin();
        await VoiceDB.create(this.toJSON());
        this.getVoiceTemplate().save();
    }

    async save() {
        await VoiceDB.update(this.toJSON(), { where: { creatorId: this.creator.id, voiceId: this.voiceChannelId } });
    }

    async load(voiceChannelId = null) {
        if (voiceChannelId) this.voiceChannelId = voiceChannelId;
        const voice = await VoiceDB.findOne({ where: { voiceId: this.voiceChannelId } });
        if (!voice) return this;
        this.creator = this.guild.members.cache.get(voice.creatorId);
        this.name = this.voiceChannel.name;
        this.voiceChannelId = voice.voiceId;
        this.textChannelId = voice.textId;
        this.voiceChannel = await this.guild.channels.cache.get(this.voiceChannelId);
        this.textChannel = await this.guild.channels.cache.get(this.textChannelId);
        this.whitelist = voice.whitelist;
        this.members = new Map(voice.members.map(m => [m, this.guild.members.cache.get(m)]));

        if (!this.voiceChannel || !this.textChannel) {
            await this.delete();
            return this;
        }
        const welcomeId = voice.welcomeId;
        if (welcomeId) {
            this.welcomeMessage = await this.textChannel.messages.fetch(welcomeId);
        }
        this.creationTimestamp = this.voiceChannel.createdTimestamp;

        this.loaded = true;
        return this;
    }

    async checkDelete() {
        if (!this.loaded) return false;
        const checkDate = new Date(this.creationTimestamp + 1000 * 60 * Voice.MINUTES);
        if (checkDate < Date.now()) {
            if (this.voiceChannel.members.size === 0) {
                await this.delete();
                return true;
            }
        }
        return false;
    }

    async delete() {
        await VoiceDB.destroy({ where: { creatorId: this.creator.id } });
        if (this.voiceChannel) await this.voiceChannel.delete();
        if (this.textChannel) await this.textChannel.delete();
    }

    async addMember(member) {
        if (this.members.has(member.id) || member.id === this.guild.client.user.id) return false;
        const overwrites = [...this.voiceChannel.permissionOverwrites.cache.values()];
        if (this.whitelist) {
            const allowPermission = Voice.getAllowPermission(member.id);
            overwrites.push(allowPermission);
        } else {
            const denyPermission = Voice.getDenyPermission(member.id);
            overwrites.push(denyPermission);
        }
        await this.voiceChannel.permissionOverwrites.set(overwrites);
        await this.textChannel.permissionOverwrites.set(overwrites);
        this.members.set(member.id, member);
        if (this.welcomeMessage) {
            const embed = this.welcomeMessage.embeds[0];
            const listField = embed.fields.find(f => f.name === 'Allowed People' || f.name === 'Blocked People');
            const memberString = [...this.members.keys()].map(id => userMention(id)).join('\n');
            listField.value = memberString;
            await this.welcomeMessage.edit({ embeds: [embed] });
        }
        await this.save();
        this.getVoiceTemplate().save();
        return true;
    }

    async removeMember(member) {
        if (!this.members.has(member.id) || member.id === this.guild.client.user.id) return false;
        await this.voiceChannel.permissionOverwrites.delete(member.id);
        await this.textChannel.permissionOverwrites.delete(member.id);
        this.members.delete(member.id);
        if (this.welcomeMessage) {
            const embed = this.welcomeMessage.embeds[0];
            const listField = embed.fields.find(f => f.name === 'Allowed People' || f.name === 'Blocked People');
            let memberString = [...this.members.keys()].map(id => userMention(id)).join('\n');
            if (!memberString) memberString = 'None';
            listField.value = memberString;
            await this.welcomeMessage.edit({ embeds: [embed] });
        }
        await this.save();
        this.getVoiceTemplate().save();
        return true;
    }

    static getAllowPermission(id, type = 'member') {
        return {
            id,
            allow: ['VIEW_CHANNEL'],
            type,
        };
    }

    static getDenyPermission(id, type = 'member') {
        return {
            id,
            deny: ['VIEW_CHANNEL'],
            type,
        };
    }

    getVoiceTemplate() {
        return new VoiceLast(this.creator, this.name, this.whitelist, this.members);
    }
}

class VoiceLast {
    constructor(member, name = '', whitelist = false, members = new Map()) {
        this.member = member;
        this.name = name;
        this.whitelist = whitelist;
        this.members = members;
    }

    toJSON() {
        return {
            creatorId: this.member.id,
            name: this.name,
            whitelist: this.whitelist,
            members: [...this.members.keys()],
        };
    }

    async load(member = this.member) {
        const data = await VoiceTemplate.findOne({ where: { creatorId: member.id } });
        if (!data) return this;
        this.name = data.name;
        this.whitelist = data.whitelist;
        const memList = data.members.map(m => [m, member.guild.members.cache.get(m)]);
        this.members = new Map(memList.filter(m => m[1]));
        return this;
    }

    async save() {
        const data = await VoiceTemplate.findOne({ where: { creatorId: this.member.id } });
        if (!data) {
            await VoiceTemplate.create(this.toJSON());
        } else {
            await data.update(this.toJSON());
        }
    }
}

module.exports = {
    Voice,
};