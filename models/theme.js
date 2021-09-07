const { Theme: ThemeDB } = require('../tools/database');

class Theme {
    /**
     * @param {Server} server Server instance
     */
    constructor(server) {
        this.server = server;
        this.guild = server.guild;
        this.name = '';
        this.guildName = this.guild.name;
        this.ranks = [];
    }

    toJSON() {
        const arrRanks = this.ranks.map(rank => rank.toJSON());
        return {
            guildId: this.guild.id,
            themeName: this.name,
            guildName: this.guildName,
            ranks: arrRanks,
        };
    }

    async insert() {
        await ThemeDB.create(this.toJSON());
        return this;
    }

    async save() {
        await ThemeDB.update(this.toJSON(), { where: { guildId: this.guild.id } });
        return this;
    }

    async load() {
        const theme = await ThemeDB.findOne({ where: { guildId: this.guild.id } });
        if (!theme) return await this.insert();
        this.name = theme.themeName;
        this.ranks = theme.ranks.map(rank => Rank.fromJSON(this, rank));
        return this;
    }

    addRank(role) {
        if (this.getRank(role)) return false;
        this.ranks.push(new Rank(this, role));
        this.save();
        return true;
    }

    getRank(role) {
        return this.ranks.find(rank => rank.role.id === role?.id || rank.role.id === role);
    }

    setRank(role, name, max) {
        const rank = this.getRank(role);
        rank.name = name;
        rank.maxMembers = max;
        rank.role.edit({ name: name });
        this.save();
    }

    removeRank(role) {
        const rank = this.getRank(role);
        if (!rank) return false;
        this.ranks.splice(this.ranks.indexOf(rank), 1);
        this.save();
        return true;
    }

    sortRanks() {
        this.ranks.sort((a, b) => -a.role.comparePositionTo(b.role));
        this.save();
    }

    getCurrentRankIndex(member) {
        const roles = Array.from(member.roles.cache.values());
        roles.sort((a, b) => b.position - a.position);
        for (const rank of roles) {
            const themeRank = this.getRank(rank);
            if (themeRank) return this.ranks.indexOf(themeRank);
        }
        return undefined;
    }

    getCurrentRank(member) {
        const index = this.getCurrentRankIndex(member);
        if (index === undefined) return undefined;
        return this.ranks[index];
    }

    async deleteAllButRank(member, rank) {
        for (const role of member.roles.cache.values()) {
            const themeRank = this.getRank(role);
            if (themeRank && themeRank !== rank) {
                await themeRank.removeMember(member);
            }
        }
    }

    async setMemberRank(member, rank) {
        await this.deleteAllButRank(member, rank);
        await rank.addMember(member);
        return true;
    }

    async setGuildName(name) {
        this.guildName = name;
        this.guild.edit({ name: name });
        this.save();
    }
}

class Rank {
    /**
     * @param {Theme} theme Theme instance
     * @param {Role} role Role instance
     */
    constructor(theme, role) {
        this.theme = theme;
        this.role = role;
        this.name = this.role.name;
        this.maxMembers = 0;
    }

    toJSON() {
        return {
            name: this.name,
            role: this.role.id,
            maxMembers: this.maxMembers,
        };
    }

    static fromJSON(theme, json) {
        const rank = new Rank(theme, theme.guild.roles.cache.get(json.role));
        rank.maxMembers = json.maxMembers;
        return rank;
    }

    async removeMember(member) {
        if (this.role.members.has(member.id)) {
            await member.roles.remove(this.role);
        }
    }

    async addMember(member) {
        if (!this.role.members.has(member.id)) {
            await member.roles.add(this.role);
        }
    }

    isBotOnly() {
        let result = false;
        for (const member of this.role.members.values()) {
            result = true;
            if (!member.user.bot) return false;
        }
        return result;
    }
}

module.exports = {
    Theme,
    Rank,
};