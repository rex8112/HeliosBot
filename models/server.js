const { Server: ServerDB } = require('../tools/database');
const { TopicChannel } = require('./topicChannel');
const { Theme } = require('./theme');
const { Deck } = require('./deck');
const { Voice } = require('./voice');
const { Client, Guild } = require('discord.js');

class Server {
    /**
     * @param {Client} client
     * @param {Guild} guild
     */
    constructor(client, guild) {
        this.client = client;
        this.guild = guild;
        this.name = this.guild.name;
        this.topicCategory = null;
        this.startingRole = null;
        this.quotesChannel = null;
        this.archiveCategory = null;
        this.privateCategory = null;
        this.getPrivateCategory();
        this.topics = new Map();
        this.decks = new Map();
        this.theme = null;
        this.privateVoiceChannels = new Map();
    }

    static POINTS_PER_MESSAGE = 2;
    static POINTS_PER_MINUTE = 1;


    async load() {
        const data = await ServerDB.findOne({ where: { guildId: this.guild.id } });
        if (data) {
            const topicCategoryId = data.get('topicCategoryId');
            const startingRoleId = data.get('startingRoleId');
            const quotesChannelId = data.get('quotesChannelId');
            const archiveCategoryId = data.get('archiveCategoryId');

            if (topicCategoryId) {
                this.topicCategory = this.guild.channels.cache.get(topicCategoryId);
            } else {
                this.topicCategory = null;
            }
            if (startingRoleId) {
                this.startingRole = this.guild.roles.cache.get(startingRoleId);
            } else {
                this.startingRole = null;
            }
            if (quotesChannelId) {
                this.quotesChannel = this.guild.channels.cache.get(quotesChannelId);
            } else {
                this.quotesChannel = null;
            }
            if (archiveCategoryId) {
                this.archiveCategory = this.guild.channels.cache.get(archiveCategoryId);
            } else {
                this.archiveCategory = null;
            }
            const topicPromises = await TopicChannel.getAllInGuild(this);
            Promise.all(topicPromises)
                .then((topics) => {
                    for (const topic of topics) {
                        this.topics.set(topic.channel.id, topic);
                    }
                });
            this.theme = await new Theme(this).load();
            for (const member of (await this.guild.members.fetch()).values()) {
                if (member.user.bot) continue;
                await this.newDeck(member);
            }
            await this.guild.commands.fetch();
            if (this.privateCategory) {
                for (const id of this.privateCategory.children.filter((c) => c.isVoice()).keys()) {
                    const voiceChannel = new Voice(this, id);
                    await voiceChannel.load();
                    if (voiceChannel.loaded) {
                        this.privateVoiceChannels.set(voiceChannel.textChannelId, voiceChannel);
                    }
                }
            }
        } else {
            this.name = this.guild.name;
            this.topicCategory = null;
            this.startingRole = null;
            this.quotesChannel = null;
            this.archiveCategory = null;
            this.theme = await new Theme(this).load();
            await ServerDB.create({
                guildId: this.guild.id,
                name: this.name,
            });
            this.load();
        }
        return this;
    }

    async save() {
        await ServerDB.update({
            name: this.name,
            topicCategoryId: this.topicCategory ? this.topicCategory.id : null,
            startingRoleId: this.startingRole ? this.startingRole.id : null,
            quotesChannelId: this.quotesChannel ? this.quotesChannel.id : null,
            archiveCategoryId: this.archiveCategory ? this.archiveCategory.id : null,
        }, {
            where: {
                guildId: this.guild.id,
            },
        });
    }

    async sortTopicChannels() {
        const arr = Array.from(this.topics.values());
        arr.sort((a, b) => { return a.compareToTopic(b); });
        for (let i = 0; i < arr.length; i++) {
            const topic = arr[i];
            await topic.channel.edit({ position: i });
        }
    }

    async newTopicChannel(name, description, creator) {
        const channel = await this.guild.channels.create(name, {
            parent: this.topicCategory,
        });
        const topicChannel = new TopicChannel(this, channel);
        await topicChannel.new(name, description, creator);
        this.topics.set(channel.id, topicChannel);
        this.sortTopicChannels();
        return topicChannel;
    }

    getPrivateCategory() {
        return this.privateCategory = this.guild.channels.cache.find((channel) => {
            return channel.type === 'GUILD_CATEGORY' && channel.name === 'Private Channels';
        });
    }

    async newDeck(member) {
        if (this.decks.has(member.id)) return this.decks.get(member.id);
        const deck = await new Deck(this, member).load();
        this.decks.set(member.id, deck);
        return deck;
    }

    getDeck(member) {
        return this.decks.get(member.id);
    }

    async getSortedDecks() {
        const arr = Array.from(this.decks.values());
        arr.sort((a, b) => { return a.compareToDeck(b); });
        return arr;
    }

    async checkTopicChannels() {
        for (const topicChannel of this.topics.values()) {
            try {
                await topicChannel.checkArchive();
                await topicChannel.checkIdle();
            } catch (err) {
                console.log(err);
            }
        }
    }

    async checkVoiceChannels(points) {
        for (const channel of this.guild.channels.cache.map(c => c).filter(c => c.isVoice())) {
            try {
                for (const member of channel.members.values()) {
                    const deck = this.decks.get(member.id);
                    let pointsToAdd = points;
                    if (channel.members.size <= 1) {
                        pointsToAdd = Math.floor(points / 2);
                    }
                    if (deck) {
                        deck.addPoints(pointsToAdd);
                    } else {
                        const newDeck = await this.newDeck(member);
                        newDeck.addPoints(pointsToAdd);
                    }
                }
            } catch (err) {
                console.log(err);
            }
        }
    }

    async checkPrivateVoiceChannels() {
        for (const channel of this.privateVoiceChannels.values()) {
            try {
                if (await channel.checkDelete()) {
                    this.privateVoiceChannels.delete(channel.textChannelId);
                }
            } catch (err) {
                console.log(err);
            }
        }
    }

    async checkCompetitiveRanking() {
        await this.guild.roles.fetch();
        const arr = Array.from(this.decks.values());
        const rankFillArray = [];
        for (let i = 0; i < this.theme.ranks.length; i++) {
            const rank = this.theme.ranks[i];
            if (!rank.isBotOnly()) {
                for (let j = 0; j < rank.maxMembers; j++) {
                    rankFillArray.push(rank);
                }
            }
        }
        arr.sort((a, b) => { return b.compareToDeck(a); });
        for (let i = 0; i < arr.length; i++) {
            const deck = arr[i];
            const member = deck.member;
            let rank = rankFillArray[i];
            if (rank === undefined) {
                rank = this.theme.ranks[this.theme.ranks.length - 1];
            }
            await this.theme.setMemberRank(member, rank);
        }
    }

    async newVoiceChannel(name, creator, whitelist, nsfw, members = new Map()) {
        const voice = new Voice(this);
        voice.members = members;
        await voice.build(name, creator, whitelist, nsfw);
        this.privateVoiceChannels.set(voice.textChannelId, voice);
        return voice;
    }

    async showArchive(member) {
        const channel = this.archiveCategory;
        if (channel) {
            await channel.permissionOverwrites.create(member.id, { 'VIEW_CHANNEL': true }, { type: 1 });
            return true;
        }
        return false;
    }

    async hideArchive(member) {
        const channel = this.archiveCategory;
        if (channel) {
            await channel.permissionOverwrites.delete(member.id);
            return true;
        }
        return false;
    }
}

module.exports = { Server };