
import unicodedata

import ucd

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class UnicodeInfo(ClientPlugin):
	name = 'unicode_info'

	defaults = {
		'ucd_cache': None
	}

	ucd = None

	def init(self):
		if self.config.ucd_cache:
			self.ucd = ucd.UCD.from_cache(self.config.ucd_cache)

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

		name, category = self.get_info(char)

		reply = (
			"U+{ord:04X} {name!r}[{category}] ({url})"
		).format(
			ord=ord(char),
			name=name,
			category=category,
			url='https://www.fileformat.info/info/unicode/char/{:x}/index.htm'.format(ord(char)),
		)
		self.reply(msg, reply)

	def get_info(self, char):
		if self.ucd:
			try:
				cp = self.ucd.by_char(char)
			except KeyError:
				return 'UNKNOWN', '??'
			return cp.name, cp.category
		else:
			return unicodedata.name(char, 'UNKNOWN'), unicodedata.category(char)


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
		# is it a character name? fast lookup first
		try:
			return unicodedata.lookup(arg)
		except KeyError:
			pass
		# now slower, more extensive lookup
		if self.ucd:
			try:
				return unichr(self.ucd.by_name(arg).value)
			except (KeyError, ValueError):
				pass
		# otherwise
		raise ValueError
