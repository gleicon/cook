"""
Cook CLI - plan and apply infrastructure configs.

Commands:
    cook plan <config.py>    - Show what would change
    cook apply <config.py>   - Apply configuration
    cook version             - Show version
"""

import click
import sys
import importlib.util
from pathlib import Path
from typing import Optional

from cook.core.executor import get_executor, reset_executor
from cook.core.resource import Action, Platform


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Cook - Modern configuration management in Python."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--host', help='Remote host for SSH')
@click.option('--user', help='SSH username')
@click.option('--key', help='SSH private key file')
@click.option('--port', default=22, help='SSH port (default: 22)')
@click.option('--sudo', is_flag=True, help='Use sudo for remote commands')
def plan(config_file: str, host: Optional[str], user: Optional[str],
         key: Optional[str], port: int, sudo: bool):
    """
    Show what would change without applying.

    Example:
        cook plan server.py
        cook plan server.py --host server.example.com --user admin
    """
    reset_executor()

    if host:
        click.echo(f"Planning {config_file} on {host}...\n")
        _plan_remote(config_file, host, user, key, port, sudo)
    else:
        click.echo(f"Planning {config_file}...\n")
        _plan_local(config_file)


def _plan_local(config_file: str):
    """Plan execution locally."""

    try:
        _load_config(config_file)
    except Exception as e:
        click.secho(f"Error loading config: {e}", fg="red")
        sys.exit(1)

    executor = get_executor()
    plan_result = executor.plan()

    if plan_result.has_errors:
        click.secho("Errors during planning:", fg="red")
        for error in plan_result.errors:
            click.secho(f"  ! {error}", fg="red")
        click.echo()

    if not plan_result.has_changes:
        click.secho("No changes needed.", fg="green")
        return

    click.echo("Cook will perform the following actions:\n")

    for resource_id, resource_plan in plan_result.plans.items():
        if not resource_plan.has_changes():
            continue
        _display_plan(resource_id, resource_plan)

    click.echo(f"\nPlan: {plan_result.change_count} to change")
    click.echo(f"\nRun 'cook apply {config_file}' to apply these changes.")


def _plan_remote(config_file: str, host: str, user: Optional[str],
                 key: Optional[str], port: int, sudo: bool):
    """Plan execution on remote host via SSH."""
    try:
        from cook.transport.ssh import SSHTransport
        from cook.core.executor import Executor
    except ImportError:
        click.secho("SSH transport requires paramiko: uv pip install paramiko", fg="red")
        sys.exit(1)

    # Create SSH transport
    click.echo(f"Connecting to {user or 'current_user'}@{host}:{port}...")
    try:
        transport = SSHTransport(host=host, port=port, user=user, key_file=key, sudo=sudo)
    except Exception as e:
        click.secho(f"SSH connection failed: {e}", fg="red")
        sys.exit(1)

    with transport:
        # Create executor with SSH transport
        executor = Executor(transport=transport, config_file=config_file)

        # Load config (this will register resources with the executor)
        reset_executor()
        from cook.core.executor import Registry
        Registry._executor = executor  # Use remote executor instead of global

        try:
            _load_config(config_file)
        except Exception as e:
            click.secho(f"Error loading config: {e}", fg="red")
            sys.exit(1)

        # Generate plan
        plan_result = executor.plan()

        if plan_result.has_errors:
            click.secho("Errors during planning:", fg="red")
            for error in plan_result.errors:
                click.secho(f"  ! {error}", fg="red")
            click.echo()

        if not plan_result.has_changes:
            click.secho("No changes needed.", fg="green")
            return

        click.echo("Cook will perform the following actions:\n")

        for resource_id, resource_plan in plan_result.plans.items():
            if not resource_plan.has_changes():
                continue
            _display_plan(resource_id, resource_plan)

        click.echo(f"\nPlan: {plan_result.change_count} to change")
        click.echo(f"\nRun 'cook apply {config_file} --host {host}' to apply these changes.")


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@click.option('--host', help='Remote host for SSH')
@click.option('--user', help='SSH username')
@click.option('--key', help='SSH private key file')
@click.option('--port', default=22, help='SSH port (default: 22)')
@click.option('--sudo', is_flag=True, help='Use sudo for remote commands')
def apply(config_file: str, yes: bool, host: Optional[str], user: Optional[str],
          key: Optional[str], port: int, sudo: bool):
    """
    Apply configuration changes.

    Example:
        cook apply server.py
        cook apply server.py --yes
        cook apply server.py --host server.example.com --user admin
    """
    reset_executor()

    if host:
        click.echo(f"Planning {config_file} on {host}...\n")
        _apply_remote(config_file, yes, host, user, key, port, sudo)
    else:
        click.echo(f"Planning {config_file}...\n")
        _apply_local(config_file, yes)


def _apply_local(config_file: str, yes: bool):
    """Apply execution locally."""

    # Load config
    try:
        _load_config(config_file)
    except Exception as e:
        click.secho(f"Error loading config: {e}", fg="red")
        sys.exit(1)

    # Generate plan
    executor = get_executor()
    executor.config_file = config_file
    executor.enable_state_tracking()
    plan_result = executor.plan()

    if not plan_result.has_changes:
        click.secho("No changes needed.", fg="green")
        return

    # Show what will be applied
    click.echo(f"Applying {plan_result.change_count} changes...\n")

    # Confirm (unless --yes)
    if not yes:
        if not click.confirm("Proceed with apply?"):
            click.echo("Aborted.")
            return

    # Apply changes
    apply_result = executor.apply(plan_result)

    # Show results
    click.echo()
    for resource_id in apply_result.changed_resources:
        plan = plan_result.plans.get(resource_id)
        if plan:
            symbol = _action_symbol(plan.action)
            click.echo(f"  {symbol} {resource_id} ... ", nl=False)
            click.secho("✓ Done", fg="green")

    # Show errors
    if apply_result.errors:
        click.secho("\nErrors during apply:", fg="red")
        for error in apply_result.errors:
            click.secho(f"  ! {error}", fg="red")
        sys.exit(1)

    click.secho(f"\nApply complete! ({apply_result.duration:.2f}s)", fg="green")


def _apply_remote(config_file: str, yes: bool, host: str, user: Optional[str],
                  key: Optional[str], port: int, sudo: bool):
    """Apply execution on remote host via SSH."""
    try:
        from cook.transport.ssh import SSHTransport
        from cook.core.executor import Executor
    except ImportError:
        click.secho("SSH transport requires paramiko: uv pip install paramiko", fg="red")
        sys.exit(1)

    # Create SSH transport
    click.echo(f"Connecting to {user or 'current_user'}@{host}:{port}...")
    try:
        transport = SSHTransport(host=host, port=port, user=user, key_file=key, sudo=sudo)
    except Exception as e:
        click.secho(f"SSH connection failed: {e}", fg="red")
        sys.exit(1)

    with transport:
        # Create executor with SSH transport
        executor = Executor(transport=transport, config_file=config_file)
        executor.enable_state_tracking()

        # Load config (this will register resources with the executor)
        reset_executor()
        from cook.core.executor import Registry
        Registry._executor = executor  # Use remote executor instead of global

        try:
            _load_config(config_file)
        except Exception as e:
            click.secho(f"Error loading config: {e}", fg="red")
            sys.exit(1)

        # Generate plan
        plan_result = executor.plan()

        if not plan_result.has_changes:
            click.secho("No changes needed.", fg="green")
            return

        # Show what will be applied
        click.echo(f"Applying {plan_result.change_count} changes...\n")

        # Confirm (unless --yes)
        if not yes:
            if not click.confirm("Proceed with apply?"):
                click.echo("Aborted.")
                return

        # Apply changes
        apply_result = executor.apply(plan_result)

        # Show results
        click.echo()
        for resource_id in apply_result.changed_resources:
            plan = plan_result.plans.get(resource_id)
            if plan:
                symbol = _action_symbol(plan.action)
                click.echo(f"  {symbol} {resource_id} ... ", nl=False)
                click.secho("✓ Done", fg="green")

        # Show errors
        if apply_result.errors:
            click.secho("\nErrors during apply:", fg="red")
            for error in apply_result.errors:
                click.secho(f"  ! {error}", fg="red")
            sys.exit(1)

        click.secho(f"\nApply complete! ({apply_result.duration:.2f}s)", fg="green")


@cli.command()
def version():
    """Show Cook version."""
    from cook import __version__
    click.echo(f"cook version {__version__}")


@cli.command()
def platform_info():
    """Show detected platform information."""
    plat = Platform.detect()
    click.echo("Platform Information:")
    click.echo(f"  System:  {plat.system}")
    click.echo(f"  Distro:  {plat.distro}")
    click.echo(f"  Version: {plat.version}")
    click.echo(f"  Arch:    {plat.arch}")


@cli.group()
def state():
    """Manage resource state and history."""
    pass


@state.command("list")
def state_list():
    """List all managed resources."""
    try:
        from cook.state import Store
    except ImportError:
        click.secho("State persistence not available", fg="red")
        sys.exit(1)

    with Store() as store:
        resources = store.list_resources()

        if not resources:
            click.echo("No managed resources found.")
            click.echo("Run 'cook apply' with state tracking enabled.")
            return

        click.echo(f"{'RESOURCE':<40} {'STATUS':<12} {'LAST APPLIED'}")
        click.echo("-" * 80)

        for res in resources:
            click.echo(f"{res.id:<40} {res.status:<12} {res.applied_at.strftime('%Y-%m-%d %H:%M')}")


@state.command("show")
@click.argument("resource_id")
def state_show(resource_id: str):
    """Show detailed state for a resource."""
    try:
        from cook.state import Store
    except ImportError:
        click.secho("State persistence not available", fg="red")
        sys.exit(1)

    with Store() as store:
        res = store.get_resource(resource_id)

        if not res:
            click.secho(f"Resource not found: {resource_id}", fg="red")
            sys.exit(1)

        click.echo(f"Resource: {res.id}")
        click.echo(f"Type: {res.type}")
        click.echo(f"Status: {res.status}")
        click.echo(f"Last Applied: {res.applied_at.strftime('%Y-%m-%d %H:%M:%S')} by {res.applied_by}")
        click.echo(f"Config File: {res.config_file}")
        click.echo(f"Hostname: {res.hostname}")

        click.echo("\nActual State:")
        for key, value in res.actual_state.items():
            click.echo(f"  {key}: {value}")

        # Show history
        history = store.get_history(resource_id, 5)
        if history:
            click.echo("\nRecent History:")
            for entry in history:
                symbol = "✓" if entry.success else "✗"
                click.echo(f"  {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {symbol} {entry.action} by {entry.user}")


@state.command("history")
@click.argument("resource_id")
@click.option("--limit", default=10, help="Number of history entries to show")
def state_history(resource_id: str, limit: int):
    """Show change history for a resource."""
    try:
        from cook.state import Store
    except ImportError:
        click.secho("State persistence not available", fg="red")
        sys.exit(1)

    with Store() as store:
        history = store.get_history(resource_id, limit)

        if not history:
            click.echo(f"No history found for {resource_id}")
            return

        click.echo(f"History for {resource_id}:\n")

        for entry in history:
            symbol = "✓" if entry.success else "✗"
            click.echo(f"{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {symbol} {entry.action} by {entry.user}@{entry.hostname}")

            if entry.changes:
                click.echo("  Changes:")
                for field, change in entry.changes.items():
                    click.echo(f"    {field}: {change.get('from')} → {change.get('to')}")
            click.echo()


@state.command("drift")
def state_drift():
    """Show resources that have drifted."""
    try:
        from cook.state import Store
    except ImportError:
        click.secho("State persistence not available", fg="red")
        sys.exit(1)

    with Store() as store:
        drifted = store.list_drifted()

        if not drifted:
            click.secho("No drifted resources found.", fg="green")
            return

        click.secho(f"Found {len(drifted)} resource(s) with drift:", fg="yellow")

        for res in drifted:
            click.echo(f"  {res.id}")
            click.echo(f"    Last applied: {res.applied_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"    Config: {res.config_file}")


@cli.group()
def record():
    """Record manual changes and generate configs."""
    pass


@record.command("start")
@click.option('--output', '-o', default='recording.json', help='Recording file')
@click.option('--watch', multiple=True, default=['/etc'], help='Paths to watch')
def record_start(output: str, watch: tuple):
    """
    Start recording terminal session.

    Captures commands and file changes, then generates Cook config.

    Example:
        sudo cook record start
        sudo cook record start --watch /etc --watch /var/www
    """
    try:
        from cook.record.recorder import RecordingSession
    except ImportError as e:
        click.secho(f"Recording not available: {e}", fg="red")
        sys.exit(1)

    session = RecordingSession(watch_paths=list(watch))

    try:
        session.start()
    except KeyboardInterrupt:
        click.echo("\n\nRecording interrupted")

    # Save recording
    session.save(output)

    # Ask to generate code
    if click.confirm("\nGenerate Cook config from recording?", default=True):
        config_file = output.replace('.json', '.py')
        session.generate_code(config_file)
        click.echo(f"\nTo test: cook plan {config_file}")


@record.command("generate")
@click.argument('recording_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output config file')
def record_generate(recording_file: str, output: str):
    """
    Generate Cook config from recording file.

    Example:
        cook record generate recording.json -o server.py
    """
    try:
        from cook.record.recorder import Recording
        from cook.record.parser import CommandParser
        from cook.record.generator import CodeGenerator
    except ImportError as e:
        click.secho(f"Recording not available: {e}", fg="red")
        sys.exit(1)

    if output is None:
        output = recording_file.replace('.json', '.py')

    # Load recording
    import json
    with open(recording_file, 'r') as f:
        data = json.load(f)

    # Parse commands
    parser = CommandParser()
    resources = []

    for cmd in data.get('commands', []):
        resource = parser.parse(cmd['command'])
        if resource:
            resources.append(resource)

    # Generate code
    generator = CodeGenerator()
    code = generator.generate(resources)

    # Add file changes as comments
    file_changes = data.get('file_changes', [])
    if file_changes:
        code += "\n# File changes detected:\n"
        for change in file_changes:
            code += f"# {change['operation']}: {change['path']}\n"

    # Save
    with open(output, 'w') as f:
        f.write(code)

    click.echo(f"Generated config saved to {output}")
    click.echo(f"Resources extracted: {len(resources)}")
    click.echo(f"File changes noted: {len(file_changes)}")


@cli.command()
@click.option('--fix', is_flag=True, help='Apply config to fix drift')
def check_drift(fix: bool):
    """Check for configuration drift."""
    try:
        from cook.monitor import DriftDetector
    except ImportError:
        click.secho("Drift monitoring not available", fg="red")
        sys.exit(1)

    click.echo("Checking for drift...")

    with DriftDetector() as detector:
        results = detector.check_all()

    drifted = [r for r in results if r.drifted]

    if not drifted:
        click.secho("No drift detected.", fg="green")
        return

    click.secho(f"\nDrift detected in {len(drifted)} resource(s):", fg="yellow")

    for result in drifted:
        click.echo(f"\n  {result.resource_id}")
        for key, diff in result.differences.items():
            click.echo(f"    {key}: {diff['expected']} -> {diff['actual']}")

    if fix:
        click.echo("\nApplying configs to fix drift...")
        click.echo("Not yet implemented. Use 'cook apply <config>' manually.")
    else:
        click.echo("\nRun with --fix to correct drift.")


def _load_config(config_file: str) -> None:
    """
    Load Python config file.

    The config file is executed as a Python module.
    Resources are auto-registered via global executor.
    """
    config_path = Path(config_file).resolve()

    # Load as module
    spec = importlib.util.spec_from_file_location("config", config_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load config: {config_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def _display_plan(resource_id: str, plan) -> None:
    """Display a single resource plan."""
    symbol = _action_symbol(plan.action)
    click.echo(f"  {symbol} {resource_id}")

    if plan.reason:
        click.echo(f"      reason: {plan.reason}")

    for change in plan.changes:
        click.echo(f"      {change.field}: {change.from_value} → {change.to_value}")

    click.echo()


def _action_symbol(action: Action) -> str:
    """Get symbol for action."""
    if action == Action.CREATE:
        return click.style("+", fg="green")
    elif action == Action.UPDATE:
        return click.style("~", fg="yellow")
    elif action == Action.DELETE:
        return click.style("-", fg="red")
    else:
        return " "


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
