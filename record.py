
import json
import os
import socket
import weakref

from girc import message

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import EkimbotHandler


class RecordPlugin(ClientPlugin):
	"""Records messages to a file as newline-seperated JSON objects"""
	name = 'record'

	# This is a global cache of open files we're writing records to.
	# The purpose is so that two instances of this plugin can write to the same file
	# without stepping on each others toes.
	# The weakref means it will properly GC and be closed when the last plugin finishes.
	fileobjs = weakref.WeakValueDictionary()

	def init(self):
		filepath = self.config.filename
		if filepath in self.fileobjs:
			self.file = self.fileobjs[filepath]
		else:
			self.file = open(filepath, 'a')
			self.fileobjs[filepath] = self.file
		self.common_info = {
			'hostname': self.client.hostname,
			'port': self.client.port,
			'ssl': self.client.ssl,
			'bot_hostname': socket.gethostname(),
			'bot_pid': os.getpid(),
		}

	def cleanup(self):
		# We can't guarentee the fileobj will be closed correctly later, so we explicitly
		# flush just to be safe.
		self.file.flush()

	@EkimbotHandler(no_ignore=True, master=None)
	def record(self, client, msg):
		if any((
			# We don't want to log private messages to the bot
			message.match(msg, command=[message.Privmsg, message.Notice], target=lambda c, v: c.matches_nick(v)),
			# Don't log some annoying connection-meta messages.
			message.match(msg, command=(message.Ping, message.Pong, message.ISupport, 'CAP')),
		)):
			return

		# We use a blacklist of attrs not to include here, not a whitelist.
		# This allows us to capture any helper properties from specialised subclasses.
		values = {
			attr: getattr(msg, attr)
			for attr in dir(msg)
			if not any((
				attr.startswith('_'),
				attr in ('client', 'extra', 'since_received'),
				callable(getattr(msg, attr)),
			))
		}
		# For additional context, include some common info about the connection, this bot.
		values.update(self.common_info)
		values.update(bot_nick=self.client.nick)

		msg_record = json.dumps(values, default=str)
		self.file.write('{}\n'.format(msg_record))
