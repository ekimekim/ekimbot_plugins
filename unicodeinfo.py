
import random

import uninames

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class UnicodeInfo(ClientPlugin):
	name = 'unicode_info'

	def init(self):
		self.uninames = uninames.UnicodeNames(self.config.uninames)

	@CommandHandler('unicode', 1)
	def unicode_info(self, msg, *args):
		"""Give info on the given unicode character

		Can be given in form of a hex number (eg. 1f4a9, U+0001F4A9),
		a name (eg. PILE OF POO), or a single utf-8 character.
		"""
		args = ' '.join(args)

		try:
			char = self._normalize_arg(args)
		except ValueError:
			try:
				args = args.decode('utf-8')
			except UnicodeDecodeError:
				self.reply(msg, "Your message contained invalid utf-8")
			else:
				self.reply(msg, (
					"Not a single character, name or code point. "
					"Maybe it contains combining characters? "
					"Your message started with: {}"
				).format(
					' '.join('{:x}'.format(ord(c)) for c in args[:4])
				))
			return

		names = [name for name, value in self.uninames.items() if value == ord(char)]
		if not names:
			names = ['UNKNOWN']
		name = random.choice(names)
		names.remove(name)

		reply = (
			"U+{ord:04X} {name!r} ({url})"
		).format(
			ord=ord(char),
			name=name,
			url='https://www.fileformat.info/info/unicode/char/{:x}/index.htm'.format(ord(char)),
		)
		self.reply(msg, reply)
		if names:
			self.reply(msg, "Also known as: {}".format(", ".join(names)))

	def _normalize_arg(self, arg):
		"""Normalize unicode_info() arg to a single char if possible, otherwise raise ValueError."""
		# is it a hex integer, with or without prefix 'U+'?
		digits = arg[2:] if arg.upper().startswith('U+') else arg
		try:
			return unichr(int(digits, 16))
		except (ValueError, OverflowError): # either bad int or bad range for unichr
			pass
		# is it a one-character utf-8 string?
		try:
			char = arg.decode('utf-8')
		except UnicodeDecodeError:
			pass
		else:
			if len(char) == 1:
				return char
		# is it a character name?
		try:
			return unichr(self.uninames.lookup(arg))
		except KeyError:
			pass
		# otherwise
		raise ValueError
