# ServerWatcher
A highly configurable Minecraft server monitoring and restart engine for HungerBridge / Pterodactyl-based Minecraft servers.

## System requirements
|             | **Minimum** | **Recommended** |
| ----------- | ----------- | --------------- | 
|  **RAM**    |   128 MB    |      256 MB     |
| **Storage** |   256 MB    |      1 GB       |

## Prerequisites
**Pterodactyl Panel / API credentials**
- You must have the server on a Pterodactyl Panel
- You need a valid client API token
**HungerBridge**
- Install [HungerBridge from Modrinth](https://modrinth.com/project/hungerbridge) on the Minecraft server you wish to monitor
- HungerBridge supports `Fabric`, `Quilt`, `Paper`, `Purpur`, and `Folia`
**A dedicated Python environment**
- ServerWatcher requires a Python 3.14+ environment to run
*Discord bot*
- Optional. The bot must have the correct endpoints set up.
*Logging directory*
- Optional. Only necessary if you want to use file logging.

## Installation
- Download the [**ServerWatcher Pterodactyl egg**](https://github.com/iFamishedX/ServerWatcher/blob/main/eggs/serverwatcher.json)
- Import it into your desired nest in your panel
- Create a server with the egg selected
- Start the server and wait for instalation and file generation to finish
- Configure the files in config/
- Start the server again
- You're done! Just let it do its thing.
