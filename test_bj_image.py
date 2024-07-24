#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
from helios.gambling.image import testing_icon, BlackjackHandImage, BlackjackImage, BlackjackHandSplitImage
from helios.gambling.cards import Card, Hand, Values, Suits


def test_get_bj_hand_image():
    cards = [Card(Suits.hearts, Values.ace), Card(Suits.hearts, Values.king), Card(Suits.hearts, Values.queen)]
    hand = Hand()
    hand.add_cards(cards)
    hand2 = Hand()
    hand2.add_cards([Card(Suits.hearts, Values.ace), Card(Suits.hearts, Values.ace)])
    icon = testing_icon()
    name = 'Test Name'
    bet = 1000
    image_generators = [BlackjackHandSplitImage([hand, hand2], icon, name, bet) for _ in range(4)]
    image_generators[0].get_image(['lose', 'push']).show()
    # bji = BlackjackImage(BlackjackHandImage(hand, icon, 'Dealer', 0), image_generators)
    # img = bji.get_image('Waiting For Player')
    # img.resize((img.width*2, img.height*2)).save('bj_image.png')


if __name__ == '__main__':
    test_get_bj_hand_image()
