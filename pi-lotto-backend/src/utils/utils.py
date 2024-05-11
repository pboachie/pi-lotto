import yaml
import os


def load_config():

    # Get current working directory
    cwd = os.getcwd()
    configPath = os.path.join(cwd, 'config', 'config.yml')

    with open(configPath, 'r') as file:
        config = yaml.safe_load(file)
    return config
