
import logging
import time

import gevent
import requests
import twitch

from ekimbot.botplugin import ClientPlugin


class AutoHost(ClientPlugin):
	"""Should be a client plugin for a client logged into twitch,
	joined to the channel config.channel (default: our nick) with /host permissions.
	It will automatically choose a host based on given rules.
	Polls every config.interval seconds, and changes host based on gathered data.
	Rules is a list of dicts. Each rule is attempted to match in order. Rules contain keys:
		target: Required. Channel name to host.
		live: Optional. If True (default), channel must be live to match.
		times: Optional. Specifies a list of tuples (begin, end) of time intervals. If given at all,
		       it will only match between any of these pairs of times. Times are either integer epoch,
		       or tuples (day_of_week, hour, minute), where day_of_week should be an int with 0 = Monday.
		       Day of week may be omitted to specify a daily rule.
		       Both start and end must be the same type, either epoch time or week-recurring tuple.
		games: Optional. If given, should be a string or list of strings of games
		       that target must be playing one of to match.
	As a special case, if the rule would have no optional keys (ie. of form {"target": channel} only),
	then it can just be a string containing the target channel.
	"""
	name = 'autohost'
	worker = None

	defaults = {
		'channel': None, # None makes us use client.nick
		'rules': [], # do-nothing ruleset
		'interval': 30,
	}

	@property
	def channel(self):
		return self.config.channel if self.config.channel is not None else self.client.nick

	def init(self):
		self.worker = gevent.spawn(self.poll_loop)
		self.hosted = None # None means unknown. config.channel means no host. otherwise, name of currently hosted
		self.api = twitch.TwitchClient()

	def cleanup(self):
		if self.worker:
			self.worker.kill(block=False)

	def poll_loop(self):
		IGNORE_CODES = {502, 503}
		while True:
			try:
				self.check()
			except Exception as e:
				if isinstance(e, requests.HTTPError) and e.response.status_code in IGNORE_CODES:
					level = logging.INFO
				else:
					level = logging.ERROR
				self.logger.log(level, "Failed to check for new rule matches", exc_info=True)
			gevent.sleep(self.config.interval)

	def check(self):
		self.logger.debug("Checking match rules")
		now = time.time()

		channel_cache = {}

		# add implicit rules at start/end
		rules = [self.channel] + self.config.rules + [{'target': self.channel, 'live': False}]

		rules = [{'target': rule} if isinstance(rule, basestring) else rule for rule in rules]
		for rule in rules:
			if self.match(now, channel_cache, **rule):
				self.host(rule['target'])
				self.logger.debug("Checked match rules, got {!r}".format(rule['target']))
				break
		else:
			assert False, "no rules matched, not even last implicit rule"

	def host(self, target):
		if target == self.hosted:
			return
		msg = '.unhost' if target == self.channel else '.host {}'.format(target)
		self.logger.info("Running host: {}".format(msg))
		self.client.msg('#{}'.format(self.channel), msg)
		self.hosted = target

	def match(self, now, channels, target, live=True, times=None, games=None):
		channel = channels.setdefault(target, self.api.channel(target))

		if live and not channel.stream:
			return False

		if games is not None:
			if isinstance(games, basestring):
				games = games,
			if channel.game not in games:
				return False

		if times is None:
			return True
		for begin, end in times:
			try:
				begin, end = map(int, (begin, end))
			except (TypeError, ValueError):
				# tuple
				# XXX ugh
				now_tuple = time.gmtime(now)
				if len(begin) == 2:
					begin = begin[0] * 3600 + begin[1] * 60
					end = end[0] * 3600 + end[1] * 60
					now_offset = now_tuple.tm_sec + 60*now_tuple.tm_min + 3600*now_tuple.tm_hour
					modulus = 3600*24
				else:
					begin = begin[0] * 3600 * 24 + begin[1] * 3600 + begin[2] * 60
					end = end[0] * 3600 * 24 + end[1] * 3600 + end[2] * 60
					now_offset = now_tuple.tm_sec + 60*now_tuple.tm_min + 3600*now_tuple.tm_hour + 3600*24*now_tuple.tm_wday
					modulus = 3600*24*7
				if end < begin: # crosses wrap line
					end += modulus
				if now_offset < begin: # it's not valid in current cycle, try previous
					now_offset += modulus
				if begin <= now_offset < end:
					return True
			else:
				# epoch
				if begin <= now < end:
					return True
		return False
