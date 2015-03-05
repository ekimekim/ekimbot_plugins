
"""A plugin that allows users to register for a notification email service,
which will email them if the regex of their choice is mentioned in chat, and they don't respond
within a time period."""

import re
import time

import gevent

from ratelimit import DecayRateLimit, BlockingRateLimit
from girc import Handler

from ekimbot.botplugin import ClientPlugin
from ekimbot.core_plugins.logalert import send
from ekimbot.utils import pretty_interval


class BlockingDecayRateLimit(DecayRateLimit, BlockingRateLimit):
	pass


# XXX logging
class NotifyPlugin(ClientPlugin):
	name = 'notify'

	# this rate counter shared by all instances decays over time and must not exceed RATE_LIMIT
	rate_limit = BlockingDecayRateLimit(20, 600)

	# XXX hard-coded for now - *THIS SHOULD BE PER CLIENT*
	store = {
		'rules': {  # maps regex : (timeout, email)
			'ekim': (600, 'mikelang3000@gmail.com'),
		}
	}

	# maps {email : (messages, greenlet)}
	pending = None

	def init(self):
		self.pending = {}

	@Handler(command='PRIVMSG')
	def check_message(self, client, msg):
		for regex, (timeout, email) in self.store['rules'].items():
			if re.match(regex, msg.payload):
				self.schedule(email, timeout, msg)
			if email not in self.pending:
				continue
			if re.match(regex, msg.sender):
				self.clear(email)

	def schedule(self, email, timeout, message):
		if email in self.pending:
			messages, greenlet = self.pending.pop(email)
			greenlet.kill(block=False)
		else:
			messages = []
		messages.append(message)
		self.pending[email] = messages, gevent.spawn(self.waiter, email, timeout)

	def waiter(self, email, timeout):
		gevent.sleep(timeout)
		messages, greenlet = self.pending.pop(email)
		with self.rate_limit:
			subject = "ekimbot: You were mentioned in IRC on {self.client.hostname}:{self.client.port}".format(self=self),
			body_format = "{msg.target} [{time} ({time_ago} ago)] <{msg.sender}>: {msg.payload}"
			time_format = "%F %T"
			body = '\n'.join(body_format.format(msg=msg,
												time=time.strptime(time_format, time.gm_time(msg.received_at)),
												time_ago=pretty_interval(msg.time_since()))
							 for msg in messages)
			send(email, subject, body)

	def clear(self, email):
		messages, greenlet = self.pending.pop(email)
		greenlet.kill(block=False)
