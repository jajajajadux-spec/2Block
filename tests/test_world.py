import math
import unittest

from apps.server.world import Store
from packages.common.protocol import DEFAULT_AVATAR


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.store = Store(clock=lambda: self.now)
        self.data = {"gameId": "block-yard", "user": "Guest", "avatar": DEFAULT_AVATAR}

    def test_launch_ack_and_one_time_use(self):
        launch = self.store.create_launch(self.data)["launchId"]
        self.assertEqual(self.store.launch_status(launch)["status"], "pending")
        self.store.join({**self.data, "launchId": launch})
        self.assertEqual(self.store.launch_status(launch)["status"], "joined")
        with self.assertRaises(ValueError):
            self.store.join({**self.data, "launchId": launch})

    def test_launch_must_match_room(self):
        launch = self.store.create_launch(self.data)["launchId"]
        with self.assertRaises(ValueError):
            self.store.join({**self.data, "launchId": launch, "gameId": "sunset-steps"})

    def test_launch_expiry(self):
        launch = self.store.create_launch(self.data)["launchId"]
        self.now += 121
        with self.assertRaises(ValueError):
            self.store.launch_status(launch)

    def test_movement_speed_diagonal_and_stall_cap(self):
        session = self.store.join(self.data)
        self.now += 1
        world = self.store.step(session["token"], {"dx": 1, "dz": 1})
        player = world["players"][0]
        self.assertAlmostEqual(math.hypot(player["x"], player["z"]), 1)
        # Spamming requests without elapsed time cannot increase speed.
        self.store.step(session["token"], {"dx": 1, "dz": 1})
        self.assertEqual(world, self.store.snapshot("block-yard"))

    def test_world_bounds_and_obstacle_collision(self):
        session = self.store.join(self.data)
        token = session["token"]
        for _ in range(30):
            self.now += 0.25
            self.store.step(token, {"dx": 1})
        self.assertEqual(self.store.sessions[token]["player"]["x"], 15)
        self.store.sessions[token]["player"].update(x=4, z=2.9)
        self.now += .1
        world = self.store.step(token, {"dz": 1})
        self.assertLessEqual(world["players"][0]["z"], 3.21)
        self.assertFalse(self.store.collides('block-yard', 4, 0, world['players'][0]['z']))

    def test_jump_gravity_and_no_double_jump(self):
        session = self.store.join(self.data)
        token = session['token']
        self.now += .05
        first = self.store.step(token, {'jump': True})['players'][0]
        self.assertGreater(first['y'], 0)
        velocity = self.store.sessions[token]['vy']
        self.now += .05
        self.store.step(token, {'jump': True})
        self.assertLess(self.store.sessions[token]['vy'], velocity)
        for _ in range(25):
            self.now += .05
            self.store.step(token, {})
        player = self.store.sessions[token]['player']
        self.assertEqual(player['y'], 0)
        self.assertTrue(player['grounded'])

    def test_landing_on_a_platform(self):
        session = self.store.join(self.data)
        stored = self.store.sessions[session['token']]
        stored['player'].update(x=-4, y=2.5, z=4, grounded=False)
        for _ in range(20):
            self.now += .05
            self.store.step(session['token'], {})
        self.assertEqual(stored['player']['y'], 1)
        self.assertTrue(stored['player']['grounded'])

    def test_sprint_is_faster_and_validated(self):
        session = self.store.join(self.data)
        self.now += .25
        player = self.store.step(session['token'], {'dx': 1, 'sprint': True})['players'][0]
        self.assertAlmostEqual(player['x'], 1.5)
        for data in ({'sprint': 1}, {'jump': 'yes'}):
            with self.assertRaises(ValueError):
                self.store.step(session['token'], data)

    def test_coin_is_collected_only_once_per_player(self):
        session = self.store.join(self.data)
        player = self.store.sessions[session['token']]['player']
        player.update(x=3, z=0)
        for _ in range(2):
            self.now += .05
            self.store.step(session['token'], {})
        self.assertEqual(player['coins'], 1)
        self.assertEqual(player['collected'], ['0'])
        second = self.store.join(self.data)
        self.assertEqual(self.store.sessions[second['token']]['player']['coins'], 0)

    def test_checkpoint_respawn_and_lava(self):
        session = self.store.join(self.data)
        player = self.store.sessions[session['token']]['player']
        player.update(x=-4, y=4, z=-8)
        self.now += .05
        self.store.step(session['token'], {})
        self.assertEqual(player['checkpoint'], 'steps')
        player.update(x=8, y=0, z=-5)
        self.now += .05
        self.store.step(session['token'], {})
        self.assertEqual((player['x'], player['y'], player['z']), (-4,4,-8))
        player.update(x=1)
        self.store.action(session['token'], {'kind': 'respawn'})
        self.assertEqual(player['x'], -4)

    def test_build_replicates_and_requires_owner_to_remove(self):
        session = self.store.join(self.data)
        data = {'kind': 'place', 'x': 2, 'y': 0, 'z': 0, 'color': '#123456'}
        world = self.store.action(session['token'], data)
        self.assertTrue(any(b.get('owner') == session['playerId'] for b in world['blocks']))
        other = self.store.join(self.data)
        with self.assertRaises(ValueError):
            self.store.action(other['token'], {**data, 'kind': 'remove'})
        self.now += .3
        world = self.store.action(session['token'], {**data, 'kind': 'remove'})
        self.assertFalse(any(b.get('owner') == session['playerId'] for b in world['blocks']))
        self.assertFalse(any(b.get('owner') for b in self.store.snapshot('sunset-steps')['blocks']))

    def test_build_validation(self):
        session = self.store.join(self.data)
        data = {'kind': 'place', 'x': 2, 'y': 0, 'z': 0, 'color': '#123456'}
        for change in ({'x': 12}, {'y': 1}, {'x': 0}, {'x': True},
                       {'y': -1}, {'color': 'red'}, {'x': 2.5}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.store.action(session['token'], {**data, **change})
        self.store.action(session['token'], data)
        with self.assertRaises(ValueError):
            self.store.action(session['token'], {**data, 'x': 3})

    def test_wave_expires(self):
        session = self.store.join(self.data)
        world = self.store.action(session['token'], {'kind': 'wave'})
        self.assertTrue(world['players'][0]['waving'])
        self.now += 3
        self.assertFalse(self.store.snapshot('block-yard')['players'][0]['waving'])

    def test_invalid_inputs(self):
        session = self.store.join(self.data)
        for value in (float("nan"), float("inf"), True, "1", None, 2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.step(session["token"], {"dx": value})

    def test_room_isolation_and_no_token_leak(self):
        first = self.store.join(self.data)
        self.store.join({**self.data, "gameId": "sunset-steps"})
        players = self.store.snapshot("block-yard")["players"]
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["id"], first["playerId"])
        self.assertNotIn("token", str(players))

    def test_capacity_and_expired_sessions(self):
        for _ in range(16):
            self.store.join(self.data)
        with self.assertRaises(ValueError):
            self.store.join(self.data)
        self.now += 16
        session = self.store.join(self.data)
        self.assertEqual(len(self.store.sessions), 1)
        self.now += 16
        with self.assertRaises(PermissionError):
            self.store.step(session["token"], {})

