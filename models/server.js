const { Server: ServerDB } = require('../tools/database');

class Server {
    constructor(client, guild) {
        this.client = client;
        this.guild = guild;
        this.name = this.guild.name;
        this.topicCategory = null;
        this.startingRole = null;
        this.quotesChannel = null;
        this.archiveCategory = null;
    }

    async load() {
        const data = await ServerDB.findOne({ where: { guildId: this.guild.id } });
        if (data) {
            const topicCategoryId = data.topicCategoryId;
            const startingRoleId = data.startingRoleId;
            const quotesChannelId = data.quotesChannelId;
            const archiveCategoryId = data.archiveCategoryId;

            if (topicCategoryId) {
                this.topicCategory = this.guild.channels.get(topicCategoryId);
            } else {
                this.topicCategory = null;
            }
            if (startingRoleId) {
                this.startingRole = this.guild.roles.get(startingRoleId);
            } else {
                this.startingRole = null;
            }
            if (quotesChannelId) {
                this.quotesChannel = this.guild.channels.get(quotesChannelId);
            } else {
                this.quotesChannel = null;
            }
            if (archiveCategoryId) {
                this.archiveCategory = this.guild.channels.get(archiveCategoryId);
            } else {
                this.archiveCategory = null;
            }
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
}

module.exports = { Server };