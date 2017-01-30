
import itertools

import gevent
import gtools
import twitch

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


def encode_recursive(o, encoding='utf-8'):
	if isinstance(o, unicode):
		return o.encode(encoding)
	elif isinstance(o, dict):
		return {encode_recursive(k): encode_recursive(v) for k, v in o.items()}
	elif isinstance(o, list):
		return [encode_recursive(x) for x in o]
	else:
		return o


class WhoIsLive(ClientPlugin):
	"""Should be a client plugin for a client logged into twitch.
	Upon request, will list all live channels out of the list of channels that config.target
	(default client.nick) is following.
	"""
	name = 'whoislive'

	defaults = {
		'target': None, # None makes us use client.nick
		'limit': 3,
	}

	@property
	def target(self):
		return self.config.target if self.config.target is not None else self.client.nick

	def init(self):
		self.api = twitch.TwitchClient()

	@CommandHandler("live", 0)
	def whoislive(self, msg, *channels):
		"""List currently live streamers

		Specify list of channels, or list of all channels followed by a channel by prepending a ~
		If nothing given, a default follow list is used depending on bot config
		"""
		found = []
		errors = False
		if not channels:
			channels = [self.target]
		try:
			# flatten iterators of follows and direct channel names into single iterable
			# TODO this could be better parallelised so follow fetches happen in parallel
			# but we need to refactor to use gevent queues or it gets real ugly real fast
			channels = itertools.chain(*[
				self.following(channel.lstrip('~')) if channel.startswith('~') else (channel,)
				for channel in channels
			])
			for name, channel in gtools.gmap_unordered(self.get_channel_if_live, channels):
				if not channel:
					continue
				found.append(name)
				if len(found) < self.config.limit:
					self.reply(msg, "https://twitch.tv/{name} is playing {game}: {status}".format(**channel))
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

	def following(self, target):
		"""Yields channel names that target is following"""
		for result in self.api.get_all("follows", "users", target, "follows", "channels"):
			yield encode_recursive(result['channel']['name'])

	def get_channel_if_live(self, name):
		"""Returns an up-to-date channel object if channel is currently live, else None"""
		stream = gevent.spawn(lambda: self.api.get("streams", name))
		channel = gevent.spawn(lambda: self.api.get("channels", name))
		if stream.get().get("stream") is None:
			return
		return encode_recursive(channel.get())
