import typer

from peercache.parser.peer import Peer
from peercache.parser.network import Network
from peercache.parser.manager import NetworkManager
from peercache.parser.registry import list_peers as registry_list


app = typer.Typer()
manager: NetworkManager = NetworkManager()


@app.command("manager")
def network_manager(
    show: bool = typer.Option(False, "--show", help="Show all current networks."),
    create: str = typer.Option(None, "--create", help="Create a new network."),
    delete: str = typer.Option(None, "--delete", help="Delete an existing network."),
):
    if show:
        typer.echo(manager.list_networks())
    elif create:
        typer.echo(manager.create_network(create))
    elif delete:
        typer.echo(manager.delete_network(delete))
    else:
        typer.echo(
            "Please provide one of the following options: --show, --create <name>, or --delete <name>."
        )


@app.command("network")
def network_command(
    name: str = typer.Argument(..., help="Name of the network."),
    show: bool = typer.Option(False, "--show", help="Show network stats."),
    add: str = typer.Option(None, "--add", help="Add a peer to the network."),
    remove: str = typer.Option(
        None, "--remove", help="Remove a peer from the network."
    ),
):
    """
    Operate on an individual network by name.
    """
    if name not in {n.name for n in manager.networks}:
        typer.echo(f"Network '{name}' not found.")
        raise typer.Exit(code=1)

    network = Network(name)

    if show:
        typer.echo(network.stats())
    elif add:
        typer.echo(network.add_peer(add))
    elif remove:
        typer.echo(network.remove_peer(remove))
    else:
        typer.echo("Use one of: --show, --add <peer>, or --remove <peer>.")


@app.command("peer")
def peer_command(
    start: str = typer.Option(None, "--start", help="Start a new peer with given ID."),
    stop: str = typer.Option(None, "--stop", help="Stop a peer with given ID."),
    status: bool = typer.Option(False, "--status", help="Show all active peers."),
):
    if start:
        peer = Peer(start)
        peer.start()
        typer.echo(f"Started peer '{start}'.")
    elif stop:
        peer = Peer(stop)
        peer.stop()
        typer.echo(f"Stopped peer '{stop}'.")
    elif status:
        peers = registry_list()
        if not peers:
            typer.echo("No active peers.")
        else:
            typer.echo("Active peers:\n" + "\n".join(f"  - {p}" for p in peers))
    else:
        typer.echo("Use one of: --start <id>, --stop <id>, or --status.")


if __name__ == "__main__":
    app()
