from collections import namedtuple
import time
import re

import signaltimeout

from girc import Handler
from girc.message import Notice, Privmsg

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

TIME_FORMAT = "%F %T UTC"

def human_list(words):
	"""Returns 'x, y and z' given a list [x,y,z] or similar for other lengths"""
	if len(words) == 0:
		return ''
	rest, last = words[:-1], words[-1]
	if not rest:
		return last
	return '{}, and {}'.format(', '.join(rest), last)


class Tell(namedtuple('Tell', ['sender', 'send_time', 'target', 'after', 'text'])):
	def __str__(self):
		return "{self.sender} from {send_time} to {self.target}{after}: {self.text}".format(
			self=self,
			after=("" if self.after is None else " after {}".format(
				time.strftime(TIME_FORMAT, time.gmtime(self.after))
			)),
			send_time=time.strftime(TIME_FORMAT, time.gmtime(self.send_time)),
		)


class TellPlugin(ClientPlugin):
	name = 'tell'

	defaults = {
		'max_matches': 3,
		'regex_timeout': 0.1,
	}

	def init(self):
		# name cache contains names that currently have no pending tells.
		# The value is None, or a time at which their next tell is scheduled.
		# Note that due to rtell not evicting things, there's no guarentee there is actually
		# a tell waiting at the next scheduled time.
		# TODO evict old nicks that haven't been seen in ages
		self.name_cache = {}

	@property
	def tells(self):
		return self.store.setdefault('tells', {})
	@tells.setter
	def tells(self, value):
		self.store['tells'] = value

	def add_tell(self, sender, target, after, text):
		self.tells.setdefault(sender.lower(), []).append(Tell(sender, time.time(), target, after, text))
		# invalidate matching nicks from cache
		for name in self.name_cache.keys():
			if self.match(target, name):
				# either invalidate completely, or update next scheduled time
				if after is None:
					del self.name_cache[name]
				elif self.name_cache[name] is None or self.name_cache[name] > after:
					self.name_cache[name] = after

	@CommandHandler('tell', 2)
	def tell(self, msg, target, *text):
		"""Leave a message for a user or users

		Args are TARGET MESSAGE. TARGET is any number of regexes seperated by & and should match the targets' nicks.
		"""
		targets = target.split('&')
		if not self.validate_targets(msg, targets):
			return
		for target in set(targets):
			self.add_tell(msg.sender, target, None, ' '.join(text))
		self.reply(msg, "Ok, I'll tell {} next time I see them speak".format(
			human_list(targets)
		))
		self.save_store()

	@CommandHandler('tellafter', 3)
	def tellafter(self, msg, target, after, *text):
		"""Leave a message for a user or users to be delivered after a certain time

		Args are TARGET TIME MESSAGE. TARGET is any number of regexes seperated by & and should match the targets' nicks.
		TIME, for now, must be epoch time because I'm lazy. I might fix this later.
		"""
		targets = target.split('&')
		if not self.validate_targets(msg, targets):
			return
		try:
			after = int(after)
		except ValueError:
			self.reply(msg, "Sorry, for now I only take epoch time. Yell at ekimekim to fix this.")
			return

		for target in set(targets):
			self.add_tell(msg.sender, target, after, ' '.join(text))
		self.reply(msg, "Ok, I'll tell {} next time I see them speak after {}".format(
			human_list(targets), time.strftime(TIME_FORMAT, time.gmtime(after))
		))
		self.save_store()

	def validate_targets(self, msg, targets):
		for target in targets:
			try:
				re.compile(target)
			except Exception as e:
				self.reply(msg, "Bad tell regex {!r}: {}".format(target, e))
				return False
		return True

	@CommandHandler('stells', 0)
	def stells(self, msg):
		"""Give user a list of their pending tells"""
		pending = self.tells.get(msg.sender.lower(), [])
		notice = lambda s: Notice(self.client, msg.sender, s).send()
		if not pending:
			notice("You have no pending tells")
			return
		notice("Your pending tells:")
		for tell in pending:
			notice(str(tell))

	@CommandHandler('rtell', 1)
	def rtell(self, msg, *text):
		"""Remove pending tells for given targets or text

		Checks for exact match on any target first, then for substring on text
		Multiple targets can be given seperated by &, and all tells to any of those targets will be removed.
		"""
		pending = self.tells.get(msg.sender.lower(), [])
		notice = lambda s: Notice(self.client, msg.sender, s).send()
		text = ' '.join(text)

		removed = []
		for target in text.split('&'):
			removed += [tell for tell in pending if tell.target == target]
			pending = [tell for tell in pending if tell.target != target]

		if not removed:
			removed = [tell for tell in pending if tell.text == text]
			pending = [tell for tell in pending if tell.text != text]

		if not removed:
			notice("Did not find any pending tells matching {!r}".format(text))
			return

		self.tells[msg.sender.lower()] = pending
		notice("Removed the following tells:")
		for tell in removed:
			notice(str(tell))
		self.save_store()

	@Handler(command=Privmsg)
	def check_message(self, client, msg):
		name = msg.sender.lower()
		now = time.time()

		# short circuit if name cache says no match
		if name in self.name_cache:
			until = self.name_cache[name]
			if until is None or until > now:
				return
			del self.name_cache[name]

		unmatched = {}
		matched = []
		until = None
		for tell_sender, tells in self.tells.items():
			for tell in tells:
				if len(matched) < self.config.max_matches and self.match(tell.target, name):
					if tell.after is None or now >= tell.after:
						matched.append(tell)
						continue
					elif tell.after is not None and (until is None or tell.after < until):
						# we track the next scheduled match for storage in cache later
						until = tell.after
				unmatched.setdefault(tell_sender, []).append(tell)

		assert len(matched) + sum(len(tells) for tells in unmatched.values()) == sum(len(tells) for tells in self.tells.values()), "{}, {}, {}".format(matched, unmatched, self.tells)
		assert len(matched) <= self.config.max_matches, "{}, {}".format(self.config.max_matches, matched)

		if matched:
			# update pending tells and reply with the matched tells
			self.tells = unmatched
			for tell in matched:
				self.reply(msg, "{msg.sender}: {tell.text} (from {tell.sender} at {send_time})".format(
					msg=msg, tell=tell, send_time=time.strftime(TIME_FORMAT, time.gmtime(tell.send_time)),
				))
			self.save_store()

		# we may have hit limit and not done all pending tells, if so we DON'T log this in cache
		if len(matched) <= self.config.max_matches:
			# No matches, or no matches left. Save it in cache.
			self.name_cache[name] = until

	def match(self, target, name):
		# to prevent pathological regex performance, we need to interrupt the regex engine
		# the only way to do this is by raising from a signal
		try:
			with signaltimeout.AlarmTimeout(self.config.regex_timeout):
				return re.search(target, name)
		except signaltimeout.Timeout:
			return False
