const { Sequelize, DataTypes } = require('sequelize');
const { databaseName, databaseUser, databasePassword, databaseHost, databasePort } = require('../config.json');

const sequelize = new Sequelize(databaseName, databaseUser, databasePassword, {
    host: databaseHost,
    port: databasePort,
    dialect: 'mariadb',
    dialectOptions: {
        bigNumberStrings: true,
        autoJsonMap: false,
    },
    logging: false,
});

const Server = sequelize.define('server', {
    guildId: {
        type: DataTypes.BIGINT,
        allowNull: false,
        unique: true,
    },
    name: {
        type: DataTypes.STRING,
    },
    topicCategoryId: {
        type: DataTypes.BIGINT,
    },
    startingRoleId: {
        type: DataTypes.BIGINT,
    },
    quotesChannelId: {
        type: DataTypes.BIGINT,
    },
    archiveCategoryId: {
        type: DataTypes.BIGINT,
    },
}, { timestamps: false });
Server.sync();

const Topic = sequelize.define('topic', {
    guildId: {
        type: DataTypes.BIGINT,
        allowNull: false,
    },
    channelId: {
        type: DataTypes.BIGINT,
        allowNull: false,
        unique: true,
    },
    name: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    description: {
        type: DataTypes.TEXT,
    },
    creatorId: {
        type: DataTypes.BIGINT,
        allowNull: false,
    },
    tier: {
        type: DataTypes.INTEGER,
    },
    pendingRemovalDate: {
        type: DataTypes.DATE,
    },
    pinned: {
        type: DataTypes.BOOLEAN,
        defaultValue: false,
    },
    archived: {
        type: DataTypes.BOOLEAN,
        defaultValue: false,
    },
}, { timestamps: false });
Topic.sync();

const Theme = sequelize.define('theme', {
    guildId: {
        type: DataTypes.BIGINT,
        allowNull: false,
    },
    themeName: {
        type: DataTypes.STRING,
        allowNull: false,
        defaultValue: '',
    },
    guildName: {
        type: DataTypes.STRING,
        allowNull: false,
        defaultValue: '',
    },
    ranks: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: [],
    },
}, { timestamps: false });
Theme.sync();

const Deck = sequelize.define('deck', {
    guildId: {
        type: DataTypes.BIGINT,
        allowNull: false,
    },
    userId: {
        type: DataTypes.BIGINT,
        allowNull: false,
    },
    cards: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: [],
    },
    totalPoints: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 0,
    },
    spentPoints: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 0,
    },
}, { timestamps: false });
Deck.sync();

const Voice = sequelize.define('voice', {
    creatorId: {
        type: DataTypes.BIGINT,
        allowNull: false,
        unique: true,
    },
    voiceId: {
        type: DataTypes.BIGINT,
        allowNull: false,
        unique: true,
    },
    textId: {
        type: DataTypes.BIGINT,
        allowNull: false,
        unique: true,
    },
    whitelist: {
        type: DataTypes.BOOLEAN,
        allowNull: false,
        defaultValue: false,
    },
    welcomeId: {
        type: DataTypes.BIGINT,
        allowNull: true,
    },
    members: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: [],
    },
}, { timestamps: false });

const VoiceTemplate = sequelize.define('voiceTemplate', {
    creatorId: {
        type: DataTypes.BIGINT,
        allowNull: false,
        unique: true,
    },
    name: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    whitelist: {
        type: DataTypes.BOOLEAN,
        allowNull: false,
        defaultValue: false,
    },
    members: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: [],
    },
}, { timestamps: false });

const Quote = sequelize.define('quote', {
    authorId: {
        type: DataTypes.BIGINT,
        allowNull: false,
    },
    content: {
        type: DataTypes.TEXT,
    },
    imageLink: {
        type: DataTypes.STRING,
    },
    jumpLink: {
        type: DataTypes.STRING,
        allowNull: false,
    },
    speakerIds: {
        type: DataTypes.JSON,
        allowNull: false,
        defaultValue: [],
    },
}, { timestamps: false });

module.exports = {
    Topic,
    Server,
    Theme,
    Deck,
    Voice,
    VoiceTemplate,
    Quote,
    sequelize,
};