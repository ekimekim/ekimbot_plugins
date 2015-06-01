
import string

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

CHAR_MAP = string.digits + string.lowercase

class BasesCommand(ClientPlugin):
	name = 'bases'

	@CommandHandler('base', 2)
	def convert(self, msg, num_str, old_base, new_base):
		"""NUM BASE1 BASE2: Convert a number from one base to another.
		Valid bases are 2..36"""
		try:
			old_base = int(old_base)
			new_base = int(new_base)
		except ValueError:
			self.reply(msg, "invalid base")
			return
		if any(base not in range(2, 37) for base in (old_base, new_base)):
			self.reply(msg, "invalid base")
			return
		try:
			num = int(num_str, old_base)
		except ValueError:
			self.reply(msg, "{!r} is not a valid number for base {}. Must be integer.".format(num_str, old_base))
			return

		digits = []
		while num:
			digit, num = num % new_base, num / new_base
			digits.append(digit)
		digits = [CHAR_MAP[d] for d in digits]
		result = ''.join(digits[::-1])
		self.reply(msg, "{} base {} = {} base {}".format(num_str, old_base, result, new_base))
