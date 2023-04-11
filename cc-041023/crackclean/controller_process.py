# coding=utf-8


# TODO: deprecate?
class ControllerProcess(object):

    def __init__(self, name, context, target, params):
        self.name = name
        args=(params)
        self.worker_proc = context.Process(target=target, name=name, args=args, daemon=True)

    # only for use by the parent process
    def startup(self):
        self.worker_proc.start()
        print('[' + str(self.worker_proc.pid) + '] ' + self.name)

    # only for use by the parent process
    def is_alive(self):
        return self.worker_proc.is_alive()

    # only for use by the parent process
    def shutdown(self):
        print('ControllerProcess "' + self.name + '" shutting down...')
        self.worker_proc.join()
        exit_code = self.worker_proc.exitcode
        #self.worker_proc.close()	# not until 3.7
        print('ControllerProcess "' + self.name + '" shut down.')
        return exit_code

