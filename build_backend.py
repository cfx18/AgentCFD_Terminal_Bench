"""Build only the v3 library. Tasks, private GT and runtime are explicit resources."""

from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
