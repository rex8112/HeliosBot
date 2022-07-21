import asyncio

from helios.horses import Horse, RaceHorse, Race


async def main():
    winnings = []

    for t in range(1, 6):
        horses = []
        for n in range(6):
            h = Horse.new(f'{t}.Horse{n}', 'unknown', t, None)
            horses.append(h)
        sorted_horses = sorted(horses, key=lambda x: x.quality, reverse=True)
        race_horses = [RaceHorse(h) for h in sorted_horses]
        race = Race(None)
        race.length = t * 100
        race.horses = race_horses
        print(f'======= Starting Race {t} =======')
        print(race.get_progress_string())
        await asyncio.sleep(1)
        ticks = 0
        while race.phase == 0:
            ticks += 1
            race.tick()
            print(race.get_progress_string())
            await asyncio.sleep(1)
        print(f'======= Finished Race {t} =======')
        print(f'Took {ticks} seconds to complete.')
        winning = ''
        for i, h in enumerate(race.finished):
            winning += f'{i}: {h.name} - {h.horse.quality} - {h.horse.speed} - {h.horse.acceleration} - {h.horse.stamina}\n'
        print(winning)
        winnings.append(race.finished)
    final_message = ''
    for i in range(len(winnings[0])):
        line = ''
        for x in range(len(winnings)):
            horse = winnings[x][i]
            if horse.tick_finished:
                line += f'{horse.name}:{horse.tick_finished:4}:{horse.progress:5.2f} - '
            else:
                line += f'{horse.name}: DNF:{horse.progress:6.2f} - '
        final_message += f'{line}\n'
    print(final_message)

asyncio.run(main())

