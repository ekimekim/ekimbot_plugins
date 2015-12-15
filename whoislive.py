
import gevent
import gtools
import twitch

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class WhoIsLive(ClientPlugin):
	"""Should be a client plugin for a client logged into twitch.
	Upon request, will list all live channels out of the list of channels that config.target
	(default client.nick) is following.
	"""
	name = 'whoislive'

	defaults = {
		'target': None, # None makes us use client.nick
		'limit': 5,
	}

	@property
	def target(self):
		return self.config.target if self.config.target is not None else self.client.nick

	def init(self):
		self.api = twitch.TwitchClient()

	@CommandHandler("live", 0)
	def whoislive(self, msg):
		"""List all currently live streamers from follow list"""
		found = []
		errors = False
		try:
			for name, channel in gtools.gmap_unordered(self.get_channel_if_live, self.following()):
				if not channel:
					continue
				found.append(name)
				if len(found) < self.config.limit:
					self.reply(msg, "{name} is playing {game}: {status}".format(**channel))
		except Exception:
			self.logger.exception("Error while checking who is live")
			errors = True
		if errors:
			self.reply(msg, "I had some issues talking to twitch, maybe try again later?")
		elif len(found) >= self.config.limit:
			found = found[self.config.limit - 1:]
			self.reply(msg, "And also {}".format(', '.join(found)))
		elif not found:
			self.reply(msg, "No-one is live right now, sorry!")

	def following(self):
		"""Yields channel names that self.target is following"""
		for result in self.api.get_all("follows", "users", self.target, "follows", "channels"):
			yield result['channel']['name']

	def get_channel_if_live(self, name):
		"""Returns an up-to-date channel object if channel is currently live, else None"""
		stream = gevent.spawn(lambda: self.api.get("streams", name))
		channel = gevent.spawn(lambda: self.api.get("channels", name))
		if stream.get().get("stream") is None:
			return
		return channel.get()
