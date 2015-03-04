
import os
from collections import Counter

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

words = {}
def load_dict():
	global words
	words = {}
	path = '/usr/share/dict'
	for name in os.listdir(path):
		filepath = os.path.join(path, name)
		with open(filepath) as f:
			lines = f.read()
		for line in lines.strip().split('\n'):
			count = tuple(sorted(Counter(line.lower()).items()))
			words.setdefault(count, set()).add(line)
load_dict()

class AnagramsCommand(ClientPlugin):
	name = 'anagrams'

	@CommandHandler('anagrams', 1)
	def anagrams(self, msg, *args):
		word = ' '.join(args)
		count = tuple(sorted(Counter(word.lower()).items()))
		matches = filter(lambda w: w.lower() != word.lower(), words.get(count, set()))
		if matches:
			self.reply(msg, "Anagrams of {}: {}".format(word, ', '.join(matches)))
		else:
			self.reply(msg, "No anagrams of {}".format(word))

	@CommandHandler('anagram', 1)
	def anagram(self, msg, *args):
		return self.anagrams(msg, *args)
