import random

from ekimbot import command_plugin

@command_plugin("roll", 0)
def dice(self, msg, *args):
	"""roll a number of 6-sided dice (default 1)"""
	if args:
		args = ' '.join(args).strip()
		try:
			n = int(args)
		except ValueError:
			self.reply(msg, "Sorry, I can't roll {!r} dice.".format(args))
			return
	else:
		n = 1

	if n < 1:
		self.reply(msg, "Sorry, I can't roll less than 1 die.")
		return
	if n > 100:
		self.reply(msg, "Sorry, but to prevent spam I only roll up to 100 dice at a time.")
		return

	results = [random.randint(1, 6) for x in range(n)]
	total = sum(results)

	# 0x2680-0x2685 is the unicode char for "DIE FACE-1" to "DIE FACE-6"
	die_chars = " ".join(unichr(0x2680 + value - 1).encode('utf-8') for value in results)

	if n == 1:
		output = "You rolled: {}".format(die_chars)
	else:
		output = "You rolled: {} (total: {})".format(die_chars, total)
	self.reply(msg, output)
