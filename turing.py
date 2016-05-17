import itertools

from gevent import Timeout
import gevent

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class Invalid(Exception):
	pass


class TapeTooLarge(Exception):
	pass


class Turing(ClientPlugin):
	name = 'turing'

	defaults = {
		'timeout': 10,
		'max_tape_size': 10000,
		'steps_before_yield': 100,
	}

	@CommandHandler('turing', 3)
	def run(self, msg, tape, start_pos, start_state, *rules):
		"""Run a turing machine.
		First arg is the initial tape state as a comma-seperated list of symbols, eg. 'foo,bar,bar,baz'.
		Second arg is the index into the initial tape to be the start poisition.
		Third arg is the initial state.
		Remaining args describe behaviour rules. These take the form 'state,symbol,action,new_state'
		and describe a rule where, when in the given state and reading the given symbol, the machine
		should do action and change state to new_state. Action may be one of:
			L{NUM}, R{NUM}: Move left or right NUM steps
			W{SYMBOL}: Write symbol to tape at current position
			E: Erase tape at current position (ie. write a blank symbol)
			N: Do nothing
		The machine will run until a state and symbol matching no rule is reached.
		"""

		tape = tape.split(',')

		try:
			try:
				start_pos = int(start_pos)
			except ValueError:
				raise Invalid("start position must be a number")

			parsed_rules = {}
			for rule in rules:
				try:
					state, symbol, action, new_state = rule.split(',')
					action_type, action_arg = action[0], action[1:]
					if action_type in ('L', 'R'):
						action_arg = int(action_arg)
					elif action_type in ('E', 'N'):
						if action_arg:
							raise ValueError
					elif action_type == 'W':
						pass
					else:
						raise ValueError
					parsed_rules[state, symbol] = action_type, action_arg, new_state
				except ValueError:
					raise Invalid("Badly formatted rule: {!r}".format(rule))
		except Invalid as e:
			self.reply(msg, str(e))

		machine = TuringMachine(tape, start_pos, start_state, parsed_rules, max_tape_size=self.config.max_tape_size)
		try:
			with Timeout(self.config.timeout):
				machine.run(steps_before_yield=self.config.steps_before_yield)
		except TapeTooLarge:
			self.reply(msg, "Turing machine ran for {machine.step} steps then stopped due to exceeding max tape size".format(machine=machine))
		except Timeout:
			self.reply(msg, "Turing machine ran for {machine.step} steps then timed out".format(machine=machine))
		else:
			self.reply(msg, "Turing machine ran for {machine.step} steps then halted with state {machine.state} on symbol {machine.current_symbol}".format(machine=machine))


class TuringMachine(object):
	def __init__(self, tape, start_pos, start_state, rules, max_tape_size=None):
		self.tape = dict((n, sym) for n, sym in enumerate(tape) if sym)
		self.pos = start_pos
		self.state = start_state
		self.rules = rules
		self.max_tape_size = max_tape_size
		self.step = 0
		self.halted = False

	@property
	def current_symbol(self):
		return self.tape.get(self.pos, '')

	def run_step(self):
		symbol = self.current_symbol
		if (self.state, symbol) not in self.rules:
			self.halt()
		else:
			action_type, action_arg, new_state = self.rules[self.state, symbol]
			if action_type in ('L', 'R'):
				self.pos += (1 if action_type == 'R' else -1) * action_arg
			elif action_type == 'W':
				self.tape[self.pos] = action_arg
				if self.max_tape_size is not None and len(self.tape) > self.max_tape_size:
					raise TapeTooLarge
			elif action_type == 'E':
				del self.tape[self.pos]
			self.state = new_state
			self.step += 1

	def halt(self):
		self.halted = True

	def run(self, steps_before_yield=None):
		for i in itertools.count():
			if self.halted:
				return
			if i and steps_before_yield and i % steps_before_yield == 0:
				gevent.idle()
			self.run_step()
