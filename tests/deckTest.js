const { Deck, Hand, HandFinders, Card } = require('../models/playingCards');

const hand = new Hand();
hand.add(new Card('hearts', 'A'));
hand.add(new Card('diamonds', 'A'));
hand.add(new Card('hearts', '5'));
hand.add(new Card('diamonds', '5'));
hand.add(new Card('spades', '5'));

const rf = HandFinders.getRoyalFlush(hand.cards);
const sf = HandFinders.getStraightFlush(hand.cards);
const fk = HandFinders.getFourOfAKinds(hand.cards);
const fh = HandFinders.getFullHouse(hand.cards);
const fl = HandFinders.getFlush(hand.cards);
const st = HandFinders.getStraight(hand.cards);
const tk = HandFinders.getThreeOfAKinds(hand.cards);
const pr = HandFinders.getPairs(hand.cards);
const hc = HandFinders.getHighCard(hand.cards);