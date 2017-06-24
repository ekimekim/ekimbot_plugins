
import functools
import itertools

import gevent
import gtools
import requests
import twitch

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler
from ekimbot.utils import reply_target


def encode_recursive(o, encoding='utf-8'):
	if isinstance(o, unicode):
		return o.encode(encoding)
	elif isinstance(o, dict):
		return {encode_recursive(k): encode_recursive(v) for k, v in o.items()}
	elif isinstance(o, list):
		return [encode_recursive(x) for x in o]
	else:
		return o


def requires_oauth(fn):
	@functools.wraps(fn)
	def wrapper(self, msg, *args):
		if self.config.oauth is None or self.config.target is None:
			self.reply(msg, "No twitch login configured")
			return
		return fn(self, msg, *args)
	return wrapper


class TwitchPlugin(ClientPlugin):
	"""Should be a client plugin for a client logged into twitch.
	Upon request, will list all live channels out of the list of channels that config.target
	(default client.nick) is following.
	"""
	name = 'whoislive'

	defaults = {
		'target': None, # None makes no args an error
		'limit': 3,
		'private_limit': 10,
		'client_id': None,
		'oauth': None, # if not none, can do follow actions
	}

	def init(self):
		self.api = twitch.TwitchClient(oauth=self.config.oauth, client_id=self.config.client_id)

	def limit(self, msg):
		if msg.target == reply_target(self.client, msg):
			# public channel
			return self.config.limit
		else:
			# private message
			return self.config.private_limit

	def _live(self, msg, *channels):
		"""List currently live streamers

		Specify list of channels, or list of all channels followed by a channel by prepending a ~
		If nothing given, a default follow list is used depending on bot config
		"""
		found = []
		errors = False
		if not channels:
			if self.config.target:
				channels = ['~{}'.format(self.config.target)]
			else:
				self.reply(msg, "Please list some channels to check")
				return
		limit = self.limit(msg)
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
				found.append(channel)
				if len(found) < limit:
					self.reply(msg, self.format_channel(channel))
		except Exception:
			self.logger.exception("Error while checking who is live")
			errors = True
		if errors:
			self.reply(msg, "I had some issues talking to twitch, maybe try again later?")
		elif len(found) >= limit:
			found = found[limit - 1:]
			if len(found) == 1:
				channel, = found
				self.reply(msg, self.format_channel(channel))
			else:
				self.reply(msg, "And also {}".format(', '.join(channel['name'] for channel in found)))
		elif not found:
			self.reply(msg, "No-one is live right now, sorry!")

	# Hack to get a command alias. TODO better way.
	twitch = CommandHandler("twitch", 0)(_live)
	live = CommandHandler("live", 0)(_live)

	def format_channel(self, channel):
		return "https://twitch.tv/{name} is playing {game}: {status}".format(**channel)

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

	def _follow_op(self, msg, channels, method, op_name):
		channels = sorted(list(set(channels)))
		failures = {}
		for channel in channels:
			try:
				self.api.request(method, 'users', self.config.target, 'follows', 'channels', channel, json=False)
			except requests.HTTPError as e:
				failures[channel] = str(e)
		if len(failures) == 0:
			self.reply(msg, "{}ed channels: {}".format(op_name, ' '.join(channels)))
		elif len(failures) == 1:
			(channel, error), = failures.items()
			self.reply(msg, "failed to {} channel {}: {}".format(op_name, channel, error))
		else:
			self.reply(msg, "failed to {} channels: {}".format(op_name, ' '.join(sorted(failures))))

	@CommandHandler("twitch follow", 1)
	@requires_oauth
	def follow(self, msg, *channels):
		self._follow_op(msg, channels, 'PUT', 'follow')

	@CommandHandler("twitch unfollow", 1)
	@requires_oauth
	def unfollow(self, msg, *channels):
		self._follow_op(msg, channels, 'DELETE', 'unfollow')
