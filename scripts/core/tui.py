"""
tui.py - Rich Terminal User Interface

Provides a beautiful, modern CLI experience with colors,
progress bars, tables, and interactive menus.
"""

from __future__ import annotations
import sys
from typing import Optional, List, Dict, Any, Callable

# Try to import rich
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.live import Live
    from rich.layout import Layout
    from rich import box
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rich"], check=True)
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.live import Live
    from rich.layout import Layout
    from rich import box


class RichTUI:
    """Rich-based terminal user interface."""
    
    def __init__(self):
        self.console = Console()
        self.width = 60
    
    def clear(self) -> None:
        """Clear the screen."""
        self.console.clear()
    
    def header(self, title: str, subtitle: str = "") -> None:
        """Display a styled header."""
        text = Text()
        text.append(f"🚀 {title}\n", style="bold cyan")
        if subtitle:
            text.append(subtitle, style="dim")
        
        panel = Panel(
            text,
            box=box.DOUBLE,
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(panel)
    
    def section(self, title: str, icon: str = "📦") -> None:
        """Print a section header."""
        self.console.print(f"\n{icon} [bold yellow]{title}[/]")
        self.console.print("─" * 40, style="dim")
    
    def success(self, message: str) -> None:
        """Print a success message."""
        self.console.print(f"[green]✅ {message}[/]")
    
    def warning(self, message: str) -> None:
        """Print a warning message."""
        self.console.print(f"[yellow]⚠️  {message}[/]")
    
    def error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[red]❌ {message}[/]")
    
    def info(self, message: str) -> None:
        """Print an info message."""
        self.console.print(f"[blue]ℹ️  {message}[/]")
    
    def status(self, message: str) -> None:
        """Print a status message."""
        self.console.print(f"   [dim]{message}[/]")
    
    def template_table(self, templates: Dict[str, Any]) -> None:
        """Display templates in a table."""
        table = Table(
            title="Available Templates",
            box=box.ROUNDED,
            header_style="bold magenta",
            show_lines=True,
        )
        
        table.add_column("#", style="cyan", justify="center", width=3)
        table.add_column("Template", style="green", width=12)
        table.add_column("GPU", width=20)
        table.add_column("Cloud", width=10)
        table.add_column("Description", style="dim")
        
        for i, (key, t) in enumerate(templates.items(), 1):
            cloud_style = "green" if t.cloud_type == "SECURE" else "yellow"
            table.add_row(
                str(i),
                key,
                t.gpu_type_id,
                f"[{cloud_style}]{t.cloud_type}[/]",
                t.desc,
            )
        
        self.console.print(table)
    
    def pod_table(self, pods: List[Dict[str, Any]]) -> None:
        """Display running pods in a table."""
        table = Table(
            title="Active Pods",
            box=box.ROUNDED,
            header_style="bold cyan",
        )
        
        table.add_column("#", style="cyan", justify="center", width=3)
        table.add_column("Pod ID", style="green")
        table.add_column("Name", style="white")
        table.add_column("GPU", style="yellow")
        table.add_column("Cost/hr", style="magenta", justify="right")
        
        for i, pod in enumerate(pods, 1):
            gpu = pod.get("machine", {}).get("gpuDisplayName", "Unknown")
            cost = pod.get("costPerHr", 0)
            table.add_row(
                str(i),
                pod["id"][:16] + "...",
                pod.get("name", "N/A"),
                gpu,
                f"${cost:.3f}",
            )
        
        self.console.print(table)
    
    def menu(self, options: List[tuple]) -> Optional[str]:
        """Display an interactive menu and get selection.
        
        Args:
            options: List of (key, label, icon) tuples
            
        Returns:
            Selected option key or None
        """
        self.console.print()
        for key, label, icon in options:
            self.console.print(f"  [{key}] {icon} {label}")
        self.console.print()
        
        choice = Prompt.ask("Select option", default="").strip().upper()
        return choice if choice else None
    
    def prompt(self, message: str, default: str = "") -> str:
        """Get user input."""
        return Prompt.ask(message, default=default)
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """Get yes/no confirmation."""
        return Confirm.ask(message, default=default)
    
    def progress_spinner(self, description: str = "Working...") -> Progress:
        """Create a spinner progress context."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=self.console,
            transient=True,
        )
    
    def progress_bar(self) -> Progress:
        """Create a progress bar context."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )
    
    def deployment_panel(
        self,
        template: str,
        pod_id: str,
        url: str,
        ssh: str
    ) -> None:
        """Display deployment success panel."""
        content = Text()
        content.append("Template: ", style="dim")
        content.append(f"{template}\n", style="bold green")
        content.append("Pod ID:   ", style="dim")
        content.append(f"{pod_id}\n", style="cyan")
        content.append("\n")
        content.append("🌐 URL:   ", style="bold")
        content.append(f"{url}\n", style="underline blue")
        content.append("🔑 SSH:   ", style="bold")
        content.append(f"{ssh}\n", style="dim")
        
        panel = Panel(
            content,
            title="[green]✅ Deployment Complete[/]",
            border_style="green",
            box=box.ROUNDED,
        )
        self.console.print(panel)
    
    def wallet_summary(self, pods: List[Dict[str, Any]], total_hourly: float) -> None:
        """Display wallet/cost summary."""
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Label", style="dim")
        table.add_column("Value", style="bold")
        
        table.add_row("Active Pods", str(len(pods)))
        table.add_row("Burn Rate", f"[yellow]${total_hourly:.3f}/hr[/]")
        table.add_row("Daily Cost", f"[red]${total_hourly * 24:.2f}/day[/]")
        
        panel = Panel(
            table,
            title="💰 Wallet",
            border_style="yellow",
        )
        self.console.print(panel)
    
    def status_panel(self, info: Dict[str, str]) -> None:
        """Display pod status panel."""
        content = ""
        for key, value in info.items():
            content += f"[dim]{key}:[/] {value}\n"
        
        panel = Panel(
            content.strip(),
            title="📊 Pod Status",
            border_style="cyan",
        )
        self.console.print(panel)


# Singleton instance
_tui: Optional[RichTUI] = None


def get_tui() -> RichTUI:
    """Get or create the global TUI instance."""
    global _tui
    if _tui is None:
        _tui = RichTUI()
    return _tui
