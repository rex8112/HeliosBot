module.exports = {
    name: 'rateLimit',
    async execute(rateLimitData) {
        console.log('Being Rate Limited');
        console.log(rateLimitData);
    },
};