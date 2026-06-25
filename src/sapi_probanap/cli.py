from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

from sapi_probanap.agent import TranscriptAgent
from sapi_probanap.models import NewsPieceStatus
from sapi_probanap.pipeline import TranscriptPipeline
from sapi_probanap.scorer import NewsScorer
from sapi_probanap.webhook import MakeWebhookSender

load_dotenv()

app = typer.Typer(help="AI agent for extracting and scoring news from meeting transcripts.")
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _build_pipeline(
    scoring_config: Optional[Path],
    webhook_url: Optional[str],
    send_approved: bool,
    send_review: bool,
) -> TranscriptPipeline:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.")
        raise typer.Exit(1)

    agent = TranscriptAgent(api_key=api_key)
    scorer = NewsScorer(config_path=scoring_config)

    webhook: MakeWebhookSender | None = None
    effective_url = webhook_url or os.environ.get("MAKE_WEBHOOK_URL", "")
    if effective_url:
        webhook = MakeWebhookSender(effective_url)

    return TranscriptPipeline(
        agent=agent,
        scorer=scorer,
        webhook=webhook,
        send_approved=send_approved,
        send_review=send_review,
    )


def _print_results(result, output_format: str) -> None:
    if output_format == "json":
        console.print_json(result.model_dump_json(indent=2))
        return

    console.print(f"\n[bold]Meeting:[/bold] {result.meeting_context}")
    console.print(
        f"Extracted [cyan]{result.total_extracted}[/cyan] items → "
        f"[green]{len(result.approved)} approved[/green], "
        f"[yellow]{len(result.review)} review[/yellow], "
        f"[red]{len(result.rejected)} rejected[/red]"
    )

    if result.webhook_sent or result.webhook_failed:
        console.print(
            f"Webhook: [green]{result.webhook_sent} sent[/green], "
            f"[red]{result.webhook_failed} failed[/red]"
        )

    all_items = result.approved + result.review + result.rejected
    if not all_items:
        console.print("[dim]No news pieces found.[/dim]")
        return

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Status", style="bold", width=10)
    table.add_column("Score", width=7)
    table.add_column("Title", min_width=30)
    table.add_column("Category", width=15)
    table.add_column("Confidence", width=10)

    status_colors = {
        NewsPieceStatus.APPROVED: "green",
        NewsPieceStatus.REVIEW: "yellow",
        NewsPieceStatus.REJECTED: "red",
    }

    for item in all_items:
        color = status_colors[item.status]
        table.add_row(
            f"[{color}]{item.status.value}[/{color}]",
            f"{item.score.total:.1f}",
            item.news_piece.title,
            item.news_piece.category.value,
            f"{item.news_piece.confidence:.0%}",
        )

    console.print(table)


@app.command()
def process(
    transcript: Optional[Path] = typer.Argument(None, help="Path to transcript file (or omit to read from stdin)"),
    scoring_config: Optional[Path] = typer.Option(None, "--scoring-config", "-c", help="Path to scoring YAML config"),
    webhook_url: Optional[str] = typer.Option(None, "--webhook-url", "-w", help="Make.com webhook URL (overrides env)"),
    send_approved: bool = typer.Option(True, help="Send approved items to webhook"),
    send_review: bool = typer.Option(True, help="Send review items to webhook"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table or json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Process a meeting transcript and extract scored news pieces."""
    _setup_logging(verbose)

    pipeline = _build_pipeline(scoring_config, webhook_url, send_approved, send_review)

    if transcript:
        if not transcript.exists():
            console.print(f"[red]File not found:[/red] {transcript}")
            raise typer.Exit(1)
        with console.status(f"Processing [bold]{transcript.name}[/bold]…"):
            result = pipeline.run_file(transcript)
    else:
        console.print("[dim]Reading transcript from stdin…[/dim]")
        text = sys.stdin.read()
        if not text.strip():
            console.print("[red]Error:[/red] Empty input.")
            raise typer.Exit(1)
        with console.status("Processing transcript…"):
            result = pipeline.run(text)

    _print_results(result, output)


@app.command()
def score_only(
    transcript: Optional[Path] = typer.Argument(None),
    scoring_config: Optional[Path] = typer.Option(None, "--scoring-config", "-c"),
    output: str = typer.Option("table", "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Extract and score news pieces without sending to webhook."""
    _setup_logging(verbose)
    pipeline = _build_pipeline(scoring_config, None, False, False)

    if transcript:
        result = pipeline.run_file(transcript)
    else:
        text = sys.stdin.read()
        result = pipeline.run(text)

    _print_results(result, output)


if __name__ == "__main__":
    app()
