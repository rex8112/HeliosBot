module.exports = {
    name: 'guildMemberAdd',
    async execute(member) {
        const server = member.client.servers.get(member.guild.id);
        if (!member.user.bot) server.newDeck(member);
        if (server.startingRole) {
            member.addRole(server.startingRole);
        }
    },
};