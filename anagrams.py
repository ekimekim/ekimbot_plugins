
import os
from collections import Counter

import gevent
from gevent.event import AsyncResult

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


words = AsyncResult()
loader = None

def load_dict():
	global words
	_words = {}
	path = '/usr/share/dict'
	for name in os.listdir(path):
		filepath = os.path.join(path, name)
		with open(filepath) as f:
			lines = f.read()
		for n, line in enumerate(lines.strip().split('\n')):
			count = tuple(sorted(Counter(line.lower()).items()))
			_words.setdefault(count, set()).add(line)
			if n % 10000 == 0:
				gevent.sleep(0.01) # let other greenlets act
	words.set(_words)


class AnagramsCommand(ClientPlugin):
	name = 'anagrams'

	def init():
		global loader
		if not (loader or words.ready()):
			loader = gevent.spawn(load_dict)

	@CommandHandler('anagrams', 1)
	def anagrams(self, msg, *args):
		word = ' '.join(args)
		count = tuple(sorted(Counter(word.lower()).items()))
		matches = filter(lambda w: w.lower() != word.lower(), words.get().get(count, set()))
		if matches:
			self.reply(msg, "Anagrams of {}: {}".format(word, ', '.join(matches)))
		else:
			self.reply(msg, "No anagrams of {}".format(word))

	@CommandHandler('anagram', 1)
	def anagram(self, msg, *args):
		return self.anagrams(msg, *args)
