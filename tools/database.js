const { Sequelize, DataTypes } = require('sequelize');
const { databaseName, databaseUser, databasePassword, databaseHost, databasePort } = require('../config.json');

const sequelize = new Sequelize(databaseName, databaseUser, databasePassword, {
    host: databaseHost,
    port: databasePort,
    dialect: 'mariadb',
    dialectOptions: {
        bigNumberStrings: true,
    },
    // logging: false,
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

module.exports = {
    Topic,
    Server,
    sequelize,
};