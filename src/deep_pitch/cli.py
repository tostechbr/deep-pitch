"""CLI do deep-pitch.

Comandos: `baseline` (previsão estatística Dixon-Coles, sem LLM), `predict`
(previsão completa via Deep Agent: baseline + ao vivo + busca), `backtest`
(calibração honesta na Copa 2026) e `serve` (sobe a API FastAPI).
"""

from __future__ import annotations

import typer

from .tools.baseline import UnknownTeamError, predict_match

app = typer.Typer(
    help="deep-pitch — previsão dos mata-matas da Copa 2026.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _main() -> None:
    """Mantém os subcomandos nomeados (baseline · predict · backtest · serve)."""


@app.command()
def baseline(
    home: str = typer.Argument(..., help="Mandante (país em inglês, ex.: 'Norway')."),
    away: str = typer.Argument(..., help="Visitante (país em inglês, ex.: 'England')."),
    neutral: bool = typer.Option(True, help="Sede neutra (padrão em mata-mata de Copa)."),
) -> None:
    """Previsão estatística (Dixon-Coles) de um confronto de seleções."""
    try:
        r = predict_match(home, away, neutral)
    except UnknownTeamError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo(f"{r.home} {r.p_home:.0%}  |  empate {r.p_draw:.0%}  |  {r.away} {r.p_away:.0%}")
    typer.echo(
        f"placar provável {r.likely_home_goals}-{r.likely_away_goals} "
        f"(xG {r.xg_home:.1f}–{r.xg_away:.1f}) · {r.n_train} jogos desde {r.since_year}"
    )


@app.command()
def predict(
    home: str = typer.Argument(..., help="Mandante (país em inglês, ex.: 'Norway')."),
    away: str = typer.Argument(..., help="Visitante (país em inglês, ex.: 'England')."),
    neutral: bool = typer.Option(True, help="Sede neutra (padrão em mata-mata)."),
    context: str | None = typer.Option(None, help="Contexto, ex.: 'semifinal'."),
) -> None:
    """Previsão COMPLETA via Deep Agent (baseline + ao vivo + busca + síntese)."""
    from .domain import MatchRequest
    from .service import run_prediction

    typer.secho("Analisando… (baseline + dados ao vivo + notícias)", fg=typer.colors.CYAN, err=True)
    p = run_prediction(MatchRequest(home=home, away=away, neutral=neutral, context=context))
    typer.echo(
        f"\n{p.home} {p.probabilities.home_win:.0%}  |  empate {p.probabilities.draw:.0%}  "
        f"|  {p.away} {p.probabilities.away_win:.0%}"
    )
    typer.secho(
        f"Vencedor: {p.winner} ({p.scoreline}) · confiança {p.confidence:.0%}",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"\n{p.rationale}")


@app.command()
def backtest() -> None:
    """Calibração: acerto do baseline nos jogos decididos da Copa 2026 (sem leakage)."""
    from .backtest import run_backtest

    typer.secho("Ajustando em pré-Copa e avaliando os jogos do torneio…", fg=typer.colors.CYAN, err=True)
    r = run_backtest()
    typer.echo(f"Jogos avaliados: {r.n}  |  acertos de vencedor: {r.hits} ({r.hit_rate:.0%})")
    typer.echo(f"RPS médio: {r.mean_rps:.3f}  (menor = melhor; ~0.25 = chute uniforme)")
    typer.secho(f"Treinado em {r.trained_on} jogos desde {r.since_year} (só pré-Copa).", fg=typer.colors.BRIGHT_BLACK)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host."),
    port: int = typer.Option(8000, help="Porta."),
) -> None:
    """Sobe a API FastAPI (POST /predict, GET /health)."""
    import uvicorn

    uvicorn.run("deep_pitch.api.main:app", host=host, port=port)


if __name__ == "__main__":
    app()
