import asyncio
import unittest
import pytest
import pytest_asyncio
import helios.database as db
from tortoise.contrib.test import tortoise_test_context
from datetime import datetime, timedelta, timezone

async def basic_setup():
    # Servers
    s1 = await db.ServerModel.create(name='Server 1')
    s2 = await db.ServerModel.create(name='Server 2')
    s3 = await db.ServerModel.create(name='Server 3')

    # Users
    u1 = await db.MemberModel.create(member_id=1234, server=s1)
    u2 = await db.MemberModel.create(member_id=5678, server=s2)
    u3 = await db.MemberModel.create(member_id=9012, server=s3)

@pytest_asyncio.fixture
async def db_ctx():
    db_url = 'sqlite://:memory:'
    async with tortoise_test_context(['helios.database'], db_url=db_url) as ctx:
        yield ctx


class TestTransactionModels:
    @pytest.mark.asyncio
    async def test_pagination(self, db_ctx):
        await basic_setup()

        u1 = await db.MemberModel.get(member_id=1234)
        amounts = [
            100, -100, 200, 400, -300
        ]
        transactions = [
            await db.TransactionModel.create(member=u1, payee='Test', description='Test', amount=x) for x in amounts
        ]
        p1 = await db.TransactionModel.get_transactions_paginated(u1, 0, 2)
        assert len(p1) == 2
        p2 = await db.TransactionModel.get_transactions_paginated(u1, 1, 2)
        assert len(p2) == 2
        p3 = await db.TransactionModel.get_transactions_paginated(u1, 2, 2)
        assert len(p3) == 1

    @pytest.mark.asyncio
    async def test_24hr_change(self, db_ctx):
        await basic_setup()
        yesterday = datetime.now(timezone.utc) - timedelta(days=1, hours=1)

        u1 = await db.MemberModel.get(member_id=1234)
        amounts = [
            100, -100, 200, 400, -300
        ]
        transactions = [
            await db.TransactionModel.create(member=u1, payee='Test', description='Test', amount=x, created_on=yesterday) for x in amounts
        ]
        transactions += [
            await db.TransactionModel.create(member=u1, payee='Test', description='Test', amount=x) for x in amounts
        ]

        change = await db.TransactionModel.get_24hr_change(u1)
        assert change == 300

    @pytest.mark.asyncio
    async def test_24hr_transfers_out(self, db_ctx):
        await basic_setup()
        yesterday = datetime.now(timezone.utc) - timedelta(days=1, hours=1)

        u1 = await db.MemberModel.get(member_id=1234)
        amounts = [
            100, -100, 200, 400, -300
        ]
        transactions = [
            await db.TransactionModel.create(member=u1, payee='Test', description='Transferred Points', amount=x, created_on=yesterday) for x in amounts
        ]
        transactions += [
            await db.TransactionModel.create(member=u1, payee='Test', description='Transferred Points', amount=x) for x in amounts
        ]

        change = await db.TransactionModel.get_24hr_transfers_out(u1)
        assert change == -400


class TestGameModels:
    async def setup(self):
        g1 = await db.GameModel.create_game(name='Game 1', display_name='Game 1', icon='na')
        a1 = await g1.aliases.create(alias='Alias 1')
        return g1, a1

    @pytest.mark.asyncio
    async def test_aliases(self, db_ctx):
        g1, a1 = await self.setup()
        q = await db.GameModel.find_game('Game 1')
        assert q == g1
        q = await db.GameModel.find_game('Alias 1')
        assert q == g1
        q = await db.GameModel.find_game('Alias 2')
        assert q != g1

    @pytest.mark.asyncio
    async def test_playtime(self, db_ctx):
        g1, a1 = await self.setup()
        q = await g1.add_playtime(30)
        g1 = await db.GameModel.find_game('Game 1')
        assert g1.play_time == 30

    @pytest.mark.asyncio
    async def test_set_day_playtime(self, db_ctx):
        g1, a1 = await self.setup()
        q = await g1.add_playtime(30)
        g1 = await db.GameModel.find_game('Game 1')
        assert g1.last_day_playtime != 30
        q = await g1.set_day_playtime()
        g1 = await db.GameModel.find_game('Game 1')
        assert g1.last_day_playtime == 30


if __name__ == '__main__':
    unittest.main()
