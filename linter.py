import subprocess


def lint():
    _exec("black ./scripts")
    _exec("flake8 ./scripts")
    _exec("black ./api")
    _exec("flake8 ./api")

def _exec(command):
    process = subprocess.Popen(command.split())
    output, error = process.communicate()


if __name__ == "__main__":
    lint()
