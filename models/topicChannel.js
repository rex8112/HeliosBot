const { MessageEmbed, MessageActionRow, MessageButton } = require('discord.js');
const { time } = require('@discordjs/builders');
const { Topic } = require('../tools/database');

class TopicChannel {
    constructor(server, channel) {
        this.server = server;
        this.guild = server.guild;
        this.channel = channel;
        this.name = channel?.name || '';
        this.description = '';
        this.pendingRemovalDate = null;
        this.tier = 0;
        this.pinned = false;
        this.archived = false;
        this.creatorId = '';
        this.loaded = false;

        this.saveRow = new MessageActionRow()
            .addComponents(
                new MessageButton()
                    .setCustomId('saveTopic')
                    .setLabel('Save')
                    .setStyle('PRIMARY'),
            );
        TopicChannel.prototype.toString = () => { return this.name; };
    }

    findChannel(id) {
        return this.guild.channels.cache.get(id);
    }

    calculateAFKDate() {
        const tier = this.tier;
        const date = new Date(Date.now() - this.TierToDate(tier));
        return date;
    }

    calculateArchiveDate() {
        const date = new Date(Date.now() + this.TierToDate(1));
        return date;
    }

    TierToDate(tier) {
        const MilisecondsInDay = 60 * 60 * 24 * 1000;
        const durations = [
            MilisecondsInDay,
            MilisecondsInDay * 7,
            MilisecondsInDay * 14,
            MilisecondsInDay * 30,
        ];
        const miliseconds = durations[tier - 1];
        return miliseconds;
    }

    async new(name, description, creator) {
        const newEmbed = new MessageEmbed()
            .setColor('GREEN')
            .setTitle('📝New Topic')
            .setDescription(`${creator} has created a new topic.`);

        this.name = name.replace('_n_shit', '').replace(' ', '_').toLowerCase();
        this.description = description;
        this.tier = 1;
        this.creatorId = creator.user.id;
        this.loaded = true;
        await Topic.create({
            guildId: this.guild.id,
            channelId: this.channel.id,
            name: this.name,
            description: this.description,
            pendingRemovalDate: null,
            tier: this.tier,
            creatorId: creator.id,
        });
        this.channel.edit(
            {
                name: `${this.name}_n_shit`,
                topic: this.description,
            },
            {
                reason: `Topic created by ${creator.user.tag}`,
            },
        );
        await this.channel.send({ embeds: [newEmbed] });
    }

    async load() {
        if (typeof this.channel === 'number') {
            this.channel = this.findChannel(this.channel);
            if (!this.channel) {
                return false;
            }
        }
        const topic = await Topic.findOne({ where: { guildId: this.guild.id, channelId: this.channel.id } });
        if (topic) {
            this.name = topic.name;
            this.description = topic.description;
            this.pendingRemovalDate = topic.pendingRemovalDate;
            this.tier = topic.tier;
            this.pinned = topic.pinned;
            this.archived = topic.archived;
            this.creatorId = topic.creatorId;
            this.loaded = true;
        }
        return this;
    }

    async save() {
        if (!this.loaded) {
            return;
        }
        await Topic.update({
            name: this.name,
            description: this.description,
            pendingRemovalDate: this.pendingRemovalDate,
            tier: this.tier,
            pinned: this.pinned,
            archived: this.archived,
        }, {
            where: {
                guildId: this.guild.id,
                channelId: this.channel.id,
            },
        });
    }

    async delete(member) {
        if (this.loaded) {
            this.server.topics.delete(this.channel.id);
            await Topic.destroy({ where: { guildId: this.guild.id, channelId: this.channel.id } });
            await this.channel.delete(`Topic deleted by ${member.user.tag}`);
            this.loaded = false;
        }
        return this;
    }

    async queueArchive() {
        this.pendingRemovalDate = this.calculateArchiveDate();
        const queueEmbed = new MessageEmbed()
            .setColor('RED')
            .setTitle('⚠Flagged to be Archived⚠')
            .setDescription(`This channel has been flagged due to inactivity. 
            The channel will be archived ${time(this.pendingRemovalDate, 'R')} for later retrieval, assuming an admin does not remove it.`)
            .addField('Archive Time', `${time(this.pendingRemovalDate)}`);
        await this.save();
        await this.channel.send({ embeds: [queueEmbed], components: [this.saveRow] });
        this.channel.edit({ name: `🛑${this.channel.name}` }, 'Channel was idle');
    }

    async archive() {
        const archiveEmbed = new MessageEmbed()
            .setColor('GREY')
            .setTitle('Topic Archived')
            .setDescription('Topic will remain in stasis until further notice.');

        this.channel.edit({
            parent: this.server.archiveCategory ? this.server.archiveCategory : this.server.topicCategory,
            lockPermissions: true,
        }, 'Channel archived');
        this.archived = true;
        this.pendingRemovalDate = null;
        await this.save();
        await this.channel.send({ embeds: [archiveEmbed], components: [this.saveRow] });
    }

    async unarchive(author) {
        const unarchiveEmbed = new MessageEmbed()
            .setColor('GREEN')
            .setTitle('Topic Restored')
            .setDescription(`Topic has been restored at tier **${this.tier}**.`);

        const abortedEmbed = new MessageEmbed()
            .setColor('GREEN')
            .setTitle('Archive Aborted')
            .setDescription('Archive was succesfully aborted.');

        let embed;
        if (this.pendingRemovalDate) {
            this.channel.edit({
                name: this.channel.name.replace('🛑', ''),
            }, 'Channel saved');
            this.pendingRemovalDate = null;
            embed = abortedEmbed;
        }
        if (this.archived) {
            this.channel.edit({
                name: this.channel.name.replace('🛑', ''),
                parent: this.server.topicCategory,
                lockPermissions: true,
            }, 'Channel saved');
            this.archived = false;
            embed = unarchiveEmbed;
        }
        if (author) {
            embed.setAuthor(author.displayName, author.user.avatarURL());
        }
        await this.channel.send({ embeds: [embed] });
        await this.save();
    }

    async checkIdle() {
        try {
            const lastMessage = await this.channel.messages.fetch(this.channel.lastMessageId);
            const idle = lastMessage.createdAt < this.calculateAFKDate();
            if (idle && !this.archived && !this.pendingRemovalDate) {
                await this.queueArchive();
            }
        } catch (e) {
            this.channel.send('JavaScript is gay so I am putting this here to fix it.');
            console.error(`${this.channel.id}|${this.channel.lastMessageId}: ${e}`);
        }
    }

    async checkArchive() {
        if (this.pendingRemovalDate && this.pendingRemovalDate < Date.now()) {
            await this.archive();
        }
    }

    isOwner(member) {
        return member.id === this.creatorId;
    }

    compareToTopic(topic) {
        if (this.pinned && !topic.pinned) {
            return -1;
        } else if (!this.pinned && topic.pinned) {
            return 1;
        }
        if (this.name > topic.name) {
            return 1;
        } else {
            return -1;
        }
    }

    static async getAllInGuild(server) {
        const topics = await Topic.findAll({ where: { guildId: server.guild.id } });
        const channels = [];
        for (const topic of topics) {
            const channel = server.guild.channels.cache.get(topic.channelId);
            if (channel) {
                channels.push(new TopicChannel(server, channel).load());
            }
        }
        return channels;
    }
}


module.exports = { TopicChannel };