const { Server: ServerDB } = require('../tools/database');
const { TopicChannel } = require('./topicChannel');

class Server {
    constructor(client, guild) {
        this.client = client;
        this.guild = guild;
        this.name = this.guild.name;
        this.topicCategory = null;
        this.startingRole = null;
        this.quotesChannel = null;
        this.archiveCategory = null;
        this.topics = new Map();
    }

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
            const promises = await TopicChannel.getAllInGuild(this);
            Promise.all(promises)
                .then((topics) => {
                    for (const topic of topics) {
                        this.topics.set(topic.channel.id, topic);
                    }
                });
        } else {
            this.name = this.guild.name;
            this.topicCategory = null;
            this.startingRole = null;
            this.quotesChannel = null;
            this.archiveCategory = null;
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

    async checkTopicChannels() {
        for (const topicChannel of this.topics.values()) {
            await topicChannel.checkArchive();
            await topicChannel.checkIdle();
        }
    }
}

module.exports = { Server };