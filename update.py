
from easycmd import cmd, FailedProcessError

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class UpdatePlugin(ClientPlugin):
	name = 'update'
	defaults = {
		# targets maps {name: info} where info is either a string path or tuple (path, command)
		# command should be list of string and will have any instances of "{}" replaced with path.
		# command may also be None. If not None, command will be run following a git update.
		# default command (if only string path given) is pip install (or {pip_cmd} install, see below)
		'targets': {},
		'pip_cmd': 'pip',
	}

	@CommandHandler("update", 1)
	def update(self, msg, target, *ref):
		"""Update a locally managed library to a given git ref
		Fetches latest upstream, updates to given ref and installs.
		If ref is blank, uses currently checked out branch.
		Give target "list" to list known targets.
		"""
		ref = ' '.join(ref)
		# input sanitation: ref may contain leading - and be parsed as a cli option
		if ref.startswith('-'):
			self.reply(msg, "Refusing to checkout ref with leading dash - consider refs/heads/... form?")
			return

		if target == 'list':
			self.reply(msg, "Update targets: {}".format(", ".join(self.config.targets)))
			return

		if target not in self.config.targets:
			self.reply(msg, "No such update target: {}".format(target))
			return
		target_info = self.config.targets[target]
		if isinstance(target_info, basestring):
			target_dir = target_info
			target_cmd = [self.config.pip_cmd, 'install', '-U', '--no-deps', '{}/']
		else:
			target_dir, target_cmd = target_info

		if target_cmd:
			target_cmd = [arg.replace('{}', target_dir) for arg in target_cmd]

		self.logger.info("Updating {} with ref {}".format(target, ref))
		self.logger.debug("Target {} has dir {!r}, cmd {!r}".format(target, target_dir, target_cmd))
		try:
			if ref:
				self.git(target_dir, 'checkout', ref, '--')
			self.git(target_dir, 'pull', '--ff-only')
			if target_cmd:
				cmd(target_cmd)
		except FailedProcessError as e:
			self.logger.warning("Failed to update {}".format(target), exc_info=True)
			self.reply(msg, "Update {} failed: {}".format(target, e.summary()))
		else:
			self.reply(msg, "Updated {}".format(target))

	def git(self, target_dir, subcmd, *args):
		self.logger.debug("Running git {} in {} with args {}".format(subcmd, target_dir, args))
		return cmd(['git', '-C', target_dir, subcmd] + list(args))
