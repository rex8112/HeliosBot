const { MessageActionRow, MessageButton } = require('discord.js');
const { userMention } = require('@discordjs/builders');

module.exports = {
    name: 'messageCreate',
    async execute(message) {
        if (message.mentions.users.has(message.client.user.id, { ignoreEveryone: true, ignoreRoles: true })) {
            const row = new MessageActionRow()
                .addComponents(
                    new MessageButton()
                        .setCustomId('yes')
                        .setLabel('Yes')
                        .setStyle('SUCCESS'),
                );
            const guild = message.guild;
            for (const channel of guild.channels.cache.values()) {
                if (channel.isVoice() && channel.members.has(message.member.id)) {
                    const m = await message.channel.send({ content: 'Would you like to ping everyone?', components: [row] });

                    // Wait for the user to confirm
                    m.awaitMessageComponent({
                        filter: (component) => {
                            component.deferUpdate();
                            return component.user.id === message.author.id;
                        },
                        time: 30000,
                        componentType: 'BUTTON',
                    })
                        // If the user clicks the confirm button, ping everyone in the voice channel
                        // eslint-disable-next-line no-unused-vars
                        .then(i => {
                            const memberMentions = [];
                            for (const mem of channel.members.values()) {
                                memberMentions.push(userMention(mem.id));
                            }
                            message.reply(`${userMention(message.member.id)} pinged:\n${memberMentions.join(' ')}`);
                        // eslint-disable-next-line no-unused-vars
                        })
                        // If the user doesn't click the confirm button, do nothing
                        .catch(err => console.error(err))
                        // Delete the message
                        .finally(() => {
                            m.delete()
                                .catch(err => console.error(err));
                        });

                    break;
                }
            }
        }
    },
};