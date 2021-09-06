const { MessageEmbed } = require('discord.js');
const { Quote: QuoteDB, sequelize } = require('../tools/database');
const { Op } = require('sequelize');

class Quote {
    constructor(id = 0, authorId = '', content = '', imageLink = '', jumpLink = '', speakerIds = []) {
        this.id = id;
        this.authorId = authorId;
        this.content = content;
        this.imageLink = imageLink;
        this.jumpLink = jumpLink;
        this.speakerIds = speakerIds;
    }

    toJSON() {
        return {
            authorId: this.authorId,
            content: this.content,
            imageLink: this.imageLink,
            jumpLink: this.jumpLink,
            speakerIds: this.speakerIds,
        };
    }

    async toEmbed(client) {
        let author;
        try {
            author = await client.users.cache.get(this.authorId)?.tag || 'Unkown';
        } catch (e) {
            author = 'Unkown';
        }
        const speakers = [];
        for (let i = 0; i < this.speakerIds.length; i++) {
            let speaker;
            try {
                speaker = await client.users.cache.get(this.speakerIds[i])?.tag || 'Unkown';
            } catch (e) {
                console.log(e);
                speaker = 'Unkown';
            }
            speakers.push(speaker);
        }
        const embed = new MessageEmbed()
            .setColor('ORANGE')
            .setTitle(`${this.id}. Submitted by ${author}`)
            .setDescription(`${this.content || ''}\n\n[Jump Link](${this.jumpLink})`)
            .setImage(this.imageLink)
            .setFooter(speakers.join(', '));
        return embed;
    }

    async save() {
        const data = await QuoteDB.findOne({ where: { id: this.id } });
        if (data) {
            await QuoteDB.update(this.toJSON(), { where: { id: this.id } });
        } else {
            await QuoteDB.create(this.toJSON());
        }
    }

    static async getQuote(authorId = null, speakerId = null, id = null) {
        let data = null;
        const query = {};
        if (id) {
            query.id = id;
        } else if (authorId) {
            query.authorId = authorId;
        } else if (speakerId) {
            query.speakerIds = { [Op.substring]: speakerId };
        }
        data = await QuoteDB.findOne({ order: sequelize.random(), where: query });
        if (data) {
            return new Quote(data.id, data.authorId, data.content, data.imageLink, data.jumpLink, data.speakerIds);
        } else {
            return null;
        }
    }

    static async newQuote(author, message) {
        const authorId = author.id;
        const content = message.content || null;
        const imageLink = message.attachments.size > 0 ? message.attachments.first().url : null;
        const jumpLink = message.url;
        const speakerIds = [...message.mentions.users.values()].map(user => user.id);
        const quote = new Quote(undefined, authorId, content, imageLink, jumpLink, speakerIds);
        await quote.save();
        return quote;
    }
}

module.exports = {
    Quote,
};