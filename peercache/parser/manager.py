import json
from pathlib import Path
from peercache.parser.network import Network
from peercache.settings.settings import SETTINGS


class NetworkManager:
    """
    Manages a collection of named Memcached-like networks.
    Loads and saves network state from the path specified in Settings.
    """

    def __init__(self) -> None:
        """
        Initialize the NetworkManager, loading persisted networks if available.

        Args:
            settings (Settings): Configuration settings instance.
        """
        self.networks: set[Network] = set()
        self.write: bool = True
        self._load()

    def _load(self) -> None:
        """
        Load networks from the JSON file specified by settings.NETWORK_DATA_PATH.
        """
        data_path = Path(SETTINGS.NETWORK_DATA_PATH)
        if data_path.exists():
            try:
                data = json.loads(data_path.read_text())
                self.networks = {Network(name) for name in data.get("networks", [])}
            except Exception:
                self.networks = set()
        else:
            self.networks = set()

    def _save(self) -> None:
        """
        Save current networks to the JSON file specified by settings.NETWORK_DATA_PATH.
        """
        data_path = Path(SETTINGS.NETWORK_DATA_PATH)
        names = sorted(n.name for n in self.networks)
        data_path.write_text(json.dumps({"networks": names}, indent=2))

    def create_network(self, name: str) -> str:
        """
        Create a new network with the given name and persist changes.

        Args:
            name (str): Network name to create.

        Returns:
            str: Result message.
        """
        if name not in {n.name for n in self.networks}:
            self.networks.add(Network(name))
            self._save()
            return f"Network '{name}' created successfully."
        return f"Network '{name}' already exists."

    def delete_network(self, name: str) -> str:
        """
        Delete the network with the given name and persist changes.

        Args:
            name (str): Network name to delete.

        Returns:
            str: Result message.
        """
        for network in list(self.networks):
            if network.name == name:
                self.networks.remove(network)

                network_file = Path(SETTINGS.NETWORKS_FOLDER_PATH) / f"{name}.json"
                if network_file.exists():
                    network_file.unlink()

                self._save()
                return f"Network '{name}' deleted successfully."
        return f"Network '{name}' not found."

    def list_networks(self) -> str:
        """
        Return a formatted string listing all current network names.

        Returns:
            str: Networks summary.
        """
        names = sorted(n.name for n in self.networks)
        if names:
            return "Networks:\n" + "\n".join(f"  - {n}" for n in names)
        return "No networks available."

    def __str__(self) -> str:
        names = sorted(n.name for n in self.networks)
        return (
            "NetworkManager:\n"
            f"  Networks: {', '.join(names) if names else 'None'}\n"
            f"  Write   : {self.write}"
        )
