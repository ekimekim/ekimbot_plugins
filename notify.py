
"""A plugin that allows users to register for a notification email service,
which will email them if the regex of their choice is mentioned in chat, and they don't respond
within a time period."""

import re

import gevent

from decay import DecayCounter
from girc import Handler

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler
from ekimbot.core_plugins.logalert import send


# XXX logging
class NotifyPlugin(ClientPlugin):
	name = 'notify'

	# this rate counter shared by all instances decays over time and must not exceed RATE_LIMIT
	rate_counter = DecayCounter(600) # half-life of 10min
	RATE_LIMIT = 20
	RETRY_INTERVAL = 60

	# XXX hard-coded for now - *THIS SHOULD BE PER CLIENT*
	store = {
		'rules': {  # maps regex : (timeout, email)
			'ekim': (600, 'mikelang3000@gmail.com'),
		}
	}

	# XXX should be per client
	# maps {email : (messages, greenlet)}
	pending = {}

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
		if self.rate_counter.get() >= self.RATE_LIMIT:
			self.pending[email] = messages, gevent.spawn(self.waiter, email, self.RETRY_INTERVAL)
		self.rate_counter.add(1)
		send(email, "ekimbot: You were mentioned in IRC on {self.client.hostname}:{self.client.port}".format(self=self),
			'\n'.join(
				"{msg.target} <{msg.sender}>: {msg.payload}".format(msg=message)
			for message in messages)
		)

	def clear(self, email):
		messages, greenlet = self.pending.pop(email)
		greenlet.kill(block=False)
