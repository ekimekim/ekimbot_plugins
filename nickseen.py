import json
import time

import gevent

from girc import message

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler, EkimbotHandler


class NickSeen(ClientPlugin):
	"""Maintains an index of when a nick was first or last seen based on logs.
	Matches on client hostname and channel it was requested in.
	"""
	name = 'nickseen'

	# maps {channel: {nick: (timestamp, text)}}
	first_index = None
	last_index = None

	# indexer is either a greenlet if we're still indexing, or None if we've finished indexing.
	indexer = None

	# config defaults
	defaults = {
		'batch_size': 1000, # how many lines for indexer to process before yielding
		'partial_line_poll': 0.1, # weird, see code for details
	}

	def init(self):
		self.first_index = {}
		self.last_index = {}
		self.indexer = gevent.spawn(self.index, self.config.filename)

	def cleanup(self):
		if self.indexer:
			self.indexer.kill()

	def index(self, filepath):
		"""We read all the historic logs, then mark the indexing process as complete.
		Note that new messages may interject in that time, so we are careful to compare
		timestamps on messages. This also prevents repeated messages (that are both written
		to the log and processed by this module upon receipt) from messing with things since
		it makes the indexes CRDTs."""
		stop = False
		with open(filepath) as f:
			for i, line in enumerate(f):
				if stop:
					# Under a weird edge case, we should stop because we know we caught up at least once
					break
				# Every so often, let other things run, as this is cpu-intensive.
				if i % self.config.batch_size == 0:
					gevent.idle()
				# Parse
				if not line.endswith('\n'):
					# partial line at end of file. we wait to see it completed with a dumb poll,
					# too much of an edge case for anything smarter.
					# We then set stop so we don't keep reading since we know we're up to date as of now,
					# but there might be more waiting by the time we check again.
					stop = True
					while '\n' not in line:
						gevent.sleep(self.config.partial_line_poll)
						line += f.read(1024)
					line, _ = line.split('\n', 1) # discard anything additional
				try:
					msg = json.loads(line)
				except Exception:
					self.logger.info('Failed to parse line {} from message record file {}, dropping'.format(i, filepath), exc_info=True)
					continue
				# filter for privmsgs from this hostname only
				if msg['command'] not in ('PRIVMSG', 'NOTICE') or msg['hostname'] != self.client.hostname:
					continue
				# check it has the expected keys, if not then log and ignore
				good = True
				for key in ('target', 'sender', 'payload', 'received_at'):
					if key not in msg:
						self.logger.info("Missing required key {} in line {} from message record file {}, dropping".format(key, i, filepath))
						good = False
						break
				if not good:
					continue
				# update the indices for the channel
				self.update_indices(msg['target'], msg['sender'], msg['received_at'], msg['payload'])
		# We're done, clear self.indexer to indicate this
		if self.indexer != gevent.getcurrent():
			self.logger.warning("Indexer finished, but self.indexer is not us? Us: {!r}, Them: {!r}".format(gevent.getcurrent(), self.indexer))
		else:
			self.logger.info("Indexer finished")
			self.indexer = None

	@EkimbotHandler(
		no_ignore=True, master=None, # always run, even on ignored nicks or if not master
		command=[message.Privmsg, message.Notice], # privmsgs and notices only
		target=lambda c, v: not c.matches_nick(v), # exclude PMs
	)
	def on_message(self, client, msg):
		self.update_indices(msg.target, msg.sender, msg.received_at, msg.payload)

	def update_indices(self, channel, nick, timestamp, text):
		channel = self.client.normalize_channel(channel)
		nick = nick.lower()
		first = self.first_index.setdefault(channel, {})
		last = self.last_index.setdefault(channel, {})
		# update first unless nick is already present and timestamp is older
		if not (nick in first and first[nick][0] < timestamp):
			first[nick] = timestamp, text
		# update last unless nick is already present and timestamp is newer
		if not (nick in last and last[nick][0] > timestamp):
			last[nick] = timestamp, text

	@CommandHandler("firstseen", 1)
	def firstseen(self, msg, *args):
		"""Show the first message in the logs for the given nick in this channel

		If asked via PM, you must specify the channel: firstseen CHANNEL NICK
		"""
		self._seen(msg, args, self.first_index, 'firstseen')

	@CommandHandler("lastseen", 1)
	def lastseen(self, msg, *args):
		"""Show the most recent message in the logs for the given nick in this channel

		If asked via PM, you must specify the channel: lastseen CHANNEL NICK
		"""
		self._seen(msg, args, self.last_index, 'lastseen')

	def _seen(self, msg, args, index, commandname):
		if self.client.matches_nick(msg.target):
			# PM, require channel
			channel, args = args[0], args[1:]
			channel = self.client.normalize_channel(channel)
		else:
			# use current channel
			channel = self.client.normalize_channel(msg.target)

		if not args:
			# only possible if we already stripped a channel arg, ie. it's a PM
			self.reply(msg, "What channel are you asking about? Format is '{} CHANNEL NICK'".format(commandname))
			return
		if len(args) > 1:
			self.reply(msg, "Too many args. Format is '{} NICK'".format(commandname))
			return

		nick, = args

		if self.indexer:
			self.reply(msg, "I'm still indexing existing logs, the following answer may be incorrect:")

		if channel not in index:
			self.reply(msg, "I don't know of any channel called {!r}".format(channel))
			return
		index = index[channel]

		if nick.lower() not in index:
			self.reply(msg, "I've never heard of this {!r} person. Are you sure they're real?".format(nick))
			return
		timestamp, text = index[nick.lower()]

		self.reply(msg, "[{timestr}] <{nick}> {text}".format(
			nick=nick, text=text,
			timestr=time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(timestamp))
		))
