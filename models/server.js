const { Server: ServerDB } = require('../tools/database');
const { TopicChannel } = require('./topicChannel');
const { Theme } = require('./theme');
const { Deck } = require('./deck');
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
        this.topics = new Map();
        this.decks = new Map();
        this.theme = null;
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
            const deckPromises = await Deck.getAllFromGuild(this);
            Promise.all(deckPromises)
                .then((decks) => {
                    for (const deck of decks) {
                        this.decks.set(deck.member.id, deck);
                    }
                });
        } else {
            this.name = this.guild.name;
            this.topicCategory = null;
            this.startingRole = null;
            this.quotesChannel = null;
            this.archiveCategory = null;
            this.theme = await new Theme(this).load();
            ServerDB.create({
                guildId: this.guild.id,
                name: this.name,
            });
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

    async newDeck(member) {
        const deck = new Deck(this, member).load();
        this.decks.set(member.id, deck);
        return deck;
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
}

module.exports = { Server };