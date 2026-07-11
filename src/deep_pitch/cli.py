"""CLI do deep-pitch.

Por ora expõe o baseline estatístico — funciona sem LLM. O comando dirigido
pelo Deep Agent (que junta baseline + dados ao vivo + busca qualitativa) entra
na Etapa 5 e vai conviver com este.
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
    """Mantém subcomandos nomeados (`baseline` agora; `predict` via agente na Etapa 5)."""


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


if __name__ == "__main__":
    app()
