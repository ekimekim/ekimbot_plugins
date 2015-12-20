
import functools
import time

import gpippy
import gevent.event
from mrpippy.connection import MessageType
from mrpippy.data import Player, Inventory
from ratelimit import BlockingRateLimit, DecayRateLimit, RateLimited

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class BlockingDecayRateLimit(DecayRateLimit, BlockingRateLimit):
	pass


def needs_data(fn):
	@functools.wraps(fn)
	def wrapper(self, msg, *args):
		if self.player is None:
			self.reply(msg, "Not ready yet, please wait.")
			return
		return fn(self, msg, *args)
	return wrapper


def op_only(fn):
	@functools.wraps(fn)
	def wrapper(self, msg, *args):
		if not msg.target.startswith('#'):
			self.reply(msg, "This command is not allowed in PM")
			return
		channel = self.client.channel(msg.target)
		if not channel.joined:
			self.reply(msg, "This command can only be used from channels I have joined")
		if msg.sender not in channel.users.ops:
			try:
				self.rate_limit.run(block=False)
				self.reply(msg, "Some of my commands are mod-only, sorry.")
			except RateLimited:
				pass
			return
		return fn(self, msg, *args)
	return wrapper


def rate_limited(fn):
	@functools.wraps(fn)
	def wrapper(self, msg, *args):
		try:
			self.rate_limit.run(block=False)
		except RateLimited:
			return
		return fn(self, msg, *args)
	return wrapper

# TODO change rate limits to simple cooldown - 1 min cooldown for each command individually
# TODO on death "!death" to target channel

class PipBoy(ClientPlugin):
	"""Plugin for interacting with a running Fallout 4 game by means of the pip boy app protocol"""
	name = 'pipboy'

	defaults = {
		'host': 'localhost',
		'port': 27000,
	}

	def init(self):
		self.pippy = gpippy.Client(self.config.host, self.config.port)
		self.ready = gevent.event.Event()
		self.rate_limit = BlockingDecayRateLimit(3, 10)

	def cleanup(self):
		super(PipBoy, self).cleanup()
		self.pippy.close()

	@property
	def player(self):
		if self.pippy.pipdata.root is None:
			return
		return Player(self.pippy.pipdata)

	@property
	def inventory(self):
		if self.pippy.pipdata.root is None:
			return
		return Inventory(self.pippy.pipdata)

	@CommandHandler('health', 0)
	@rate_limited
	@needs_data
	def health(self, msg):
		player = self.player
		limbs = {name: condition * 100 for name, condition in player.limbs.items() if condition < 1}
		limbs_str = ", ".join("{} {:.0f}%".format(name, condition) for name, condition in limbs.items())
		if not limbs_str:
			limbs_str = 'all limbs healthy'

		self.reply(msg,
			(
				"{player.name} L{level} ({level_percent}% to next), "
				"{player.hp:.0f}/{player.maxhp:.0f}hp ({hp_percent}%), {limbs}"
			).format(
				player = player,
				level = int(player.level),
				level_percent = int(100 * player.level) % 100,
				hp_percent = int(100 * player.hp / player.maxhp),
				limbs = limbs_str,
			)
		)

	@CommandHandler('weight', 0)
	@rate_limited
	@needs_data
	def weight(self, msg):
		player = self.player

		self.reply(msg,
			(
				"{player.name} carrying {player.weight:.0f}/{player.maxweight:.0f}lb "
				"in {player.location} at {time}"
			).format(
				player = player,
				time = time.strftime("%H:%M", time.gmtime(player.time)),
				special = ', '.join('{}: {}'.format(letter, value)
				                    for letter, value in zip('SPECIAL', player.special)),
			)
		)

	@CommandHandler('special', 0)
	@rate_limited
	@needs_data
	def special(self, msg):
		player = self.player
		names = "STR", "PER", "END", "CHA", "INT", "AGL", "LCK"
		display = []
		for name, value, base in zip(names, player.special, player.base_special):
			diff = value - base
			suffix = '({:+d})'.format(diff) if diff else ''
			display.append("{} {}{}".format(name, value, suffix))
		self.reply(msg, "{}: {}".format(
			player.name,
			", ".join(display),
		))

	@CommandHandler('weapons', 0)
	@rate_limited
	@needs_data
	def list_weapons(self, msg):
		# TODO remap to pc controls for fav slots (1-9, 0, -, =)
		favorites = [item for item in self.inventory.items if item.favorite]
		favorites.sort(key=lambda item: item.favorite_slot)
		self.reply(msg, "Favorited items:")
		for item in favorites:
			self.rate_limit.run(block=True)
			self.reply(msg, "{item.favorite_slot} - {item.name}".format(item=item))

	@CommandHandler('equip', 1)
#	@op_only TODO fix op detection
	@needs_data
	def equip(self, msg, index):
		# TODO remap to pc controls for fav slots (1-9, 0, -, =)
		# TODO refuse to unequip already-equipped guns
		inventory = self.inventory
		try:
			index = int(index)
		except ValueError:
			self.reply(msg, "Favorite slot must be a number, not {!r}".format(index))
			return
		items = [item for item in inventory.items if item.favorite_slot == index]
		if not items:
			self.reply(msg, "No item attached to that favorite slot")
			return
		if len(items) > 1:
			self.reply(msg, "More than one item attached to that favorite slot somehow?")
			return
		item, = items
		# todo replace with more general code
		request = self.pippy.rpc.use_item(lambda resp: None, item.handle_id, inventory.version)
		self.pippy.send(MessageType.COMMAND, request)
