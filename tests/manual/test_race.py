import asyncio

from helios.horses import Horse, RaceHorse, Race


async def main():
    winnings = []

    for t in range(1, 6):
        horses = []
        for n in range(6):
            h = Horse.new(None, f'{t}.Horse{n}', 'unknown', None)
            horses.append(h)
        sorted_horses = sorted(horses, key=lambda xh: xh.quality, reverse=True)
        race_horses = [RaceHorse(h) for h in sorted_horses]
        race = Race()
        race.horses = race_horses
        print(f'======= Starting Race {t} =======')
        print(race.get_progress_string(50))
        await asyncio.sleep(1)
        ticks = 0
        while race.phase == 0:
            ticks += 1
            race.tick()
            print(race.get_progress_string(50))
            await asyncio.sleep(0.05)
        print(f'======= Finished Race {t} =======')
        print(f'Took {ticks} seconds to complete.')
        winning = ''
        for i, h in enumerate(race.finished_horses):
            winning += f'{i}: {h.name} - {h.horse.quality} - {h.horse.speed:6.2f} - {h.horse.acceleration:6.2f} - {h.horse.stamina}\n'
        print(winning)
        winnings.append(race.finished_horses)
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

