import yaml
import os
import logging
import colorama
import uuid

# Function to load the config file
def load_config():

    # Get current working directory
    cwd = os.getcwd()
    configPath = os.path.join(cwd, 'config', 'config.yml')

    with open(configPath, 'r') as file:
        config = yaml.safe_load(file)
    return config

# Function to configure logging
def configure_logging(config):
    logging.basicConfig(
        level=config['logging']['level'],
        format=config['logging']['format'],
        handlers=[logging.StreamHandler()]
    )

    if 'filePath' in config['logging']:
        file_handler = logging.FileHandler(
            config['logging']['filePath'],
            mode='a',
            encoding=None,
            delay=False
        )
        logging.getLogger().addHandler(file_handler)

    colorama.init(autoreset=True)
