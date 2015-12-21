
import functools
import time

import gpippy
import gevent.event
from mrpippy.data import Player, Inventory

from ekimbot.botplugin import ChannelPlugin
from ekimbot.commands import ChannelCommandHandler


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
		if msg.sender not in channel.users.ops:
			if self.check_cooldown('mod-only', 30):
				self.reply(msg, "This command is mod-only.")
			return
		return fn(self, msg, *args)
	return wrapper


def with_cooldown(interval):
	"""Only run the wrapped function if it hasn't run in the last interval seconds"""
	def _with_cooldown(fn):
		@functools.wraps(fn)
		def wrapper(self, msg, *args):
			if self.check_cooldown(fn.__name__, interval):
				return fn(self, msg, *args)
		return wrapper
	return _with_cooldown


class PipBoy(ChannelPlugin):
	"""Plugin for interacting with a running Fallout 4 game by means of the pip boy app protocol"""
	name = 'pipboy'

	defaults = {
		'host': 'localhost',
		'port': 27000,
	}

	was_dead = False

	def init(self):
		self.pippy = gpippy.Client(self.config.host, self.config.port, self.on_update)
		self.ready = gevent.event.Event()
		self.cooldowns = {}

	def cleanup(self):
		super(PipBoy, self).cleanup()
		self.pippy.close()

	def check_cooldown(self, name, interval):
		"""If named cooldown has not been used in the last interval seconds,
		return True and use the cooldown. Else return False."""
		now = time.time()
		if name in self.cooldowns and now - self.cooldowns[name] < interval:
			return False
		self.cooldowns[name] = now
		return True

	def on_update(self, update):
		player = self.player
		if not player:
			return
		is_dead = player.value['Status']['IsPlayerDead']
		if is_dead and not self.was_dead:
			self.was_dead = True
			if self.check_cooldown('death', 10):
				self.channel.msg("!death")
		elif self.was_dead and not is_dead:
			self.was_dead = False

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

	@ChannelCommandHandler('health', 0)
	@with_cooldown(60)
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

	@ChannelCommandHandler('info', 0)
	@with_cooldown(60)
	@needs_data
	def info(self, msg):
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

	@ChannelCommandHandler('special', 0)
	@with_cooldown(60)
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

	@ChannelCommandHandler('weapons', 0)
	@with_cooldown(60)
	@needs_data
	def list_weapons(self, msg):
		favorites = [item for item in self.inventory.weapons if item.favorite]
		favorites.sort(key=lambda item: item.favorite_slot)
		self.reply(msg, "Favorited items:")
		for item in favorites:
			slot_name = item.favorite_slot + 1
			self.reply(msg, "{} - {}".format(slot_name, item.name))

	@ChannelCommandHandler('chems', 0)
	@with_cooldown(60)
	@needs_data
	def list_chems(self, msg):
		favorites = [item for item in self.inventory.aid if item.favorite]
		favorites.sort(key=lambda item: item.favorite_slot)
		self.reply(msg, "Favorited chems:")
		for item in favorites:
			slot_name = item.favorite_slot + 1
			description = ', '.join(item.effects_text)
			self.reply(msg, "{slot} - {item.count}x {item.name} ({description})".format(
				slot=slot_name,
				item=item,
				description=description,
			))

	@ChannelCommandHandler('equip', 1)
	@op_only
	@needs_data
	def equip(self, msg, index):
		inventory = self.inventory
		try:
			index = int(index) - 1 # user interface is 1-indexed
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
		if item.equipped:
			self.reply(msg, "Sorry, you can't equip something that's already equipped")
			return
		self.pippy.use_item(item.handle_id, inventory.version)
