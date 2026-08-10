#!/usr/bin/env python3
"""build.py — data/folhas.json (fonte) -> data.json (o que o site le).

POR QUE ESTE ARQUIVO EXISTE NO REPO (16/07/2026):
A versao anterior (build_from_folhas.py) e a fonte (folhas-confiaveis.json) viviam no
scratchpad, que e efemero. Sumiram. Sobrou so o data.json gerado, sem a fonte. Fonte e
build agora moram AQUI, versionados junto com o site.

REGRA DO TRACADO (Pietro, 17/07 — a mais importante e a mais contraintuitiva):
  **O MAPA que o Pietro manda junto e o NORTE. O nome do tracado escrito na folha
  esta QUASE SEMPRE ERRADO.** Palavras dele: "a norte e a foto que eu mandei (nome da
  pista e etc), o que ta escrito na folha normalmente sempre vai estar errado".
  Ex: folhas de 09/05 diziam "Indoor Tradicional" -> era Tracado 13 (550m).
      folhas de 08/07 e 16/07 diziam "Indoor" -> era Tracado 9 Anti-Horario (900m).
  Sanity check util: metragem/tempo. 550m ~ 35s. 900m ~ 54s.
  Sem mapa -> PERGUNTAR ao Pietro. Nunca confiar no rotulo impresso.

REGRAS (definidas pelo Pietro, 12/07):
  - So folha OFICIAL confiavel (Competikar/LapTime), com tracado + kart de cada piloto.
  - Ranking por MELHOR VOLTA, nao por posicao de corrida.
  - Dedup por nome: fica o melhor tempo do piloto; o kart mostrado e o kart DAQUELE tempo.

Adicionar folha nova: append em data/folhas.json -> `python build.py` -> git push.
"""
import json
import re
from datetime import date
from pathlib import Path

# SESSAO OFICIAL vs TREINO (Pietro, 09-10/08) — regra estrutural, nao lista manual:
#   "quando tem tipo tres grupos no mesmo dia — grupo 1, grupo 2 [...] sessoes oficiais
#   mesmo, porque dai os tempos sao mais certos" (peso padronizado a 90kg no campeonato,
#   todo mundo igual; treino livre tem gente com/sem peso misturada).
# Validado contra os dados em 10/08: CV (desvio padrao / media) do melhor_volta por
# folha e ~1.8% nas folhas Oficiais contra ~9.9% nas Treino (a diferenca vem sobretudo
# de voltas soltas/incidentes que aparecem MUITO mais em treino livre que em prova
# arbitrada com DQ/penalidade). O criterio do Pietro se sustentou — nao foi forcado.
# Sinal estrutural (nao precisa listar folha por folha, se aplica sozinho a folha nova):
#   (a) bateria em formato "Grupo N - ..." (mesmo dia, varios grupos = campeonato); ou
#   (b) evento nomeado como etapa/desafio formal ("... (Etapa N)").
_RE_GRUPO = re.compile(r"Grupo\s*\d")
_RE_ETAPA_EVENTO = re.compile(r"Etapa\s*\d")


def categoria(f: dict) -> str:
    if _RE_GRUPO.search(f.get("bateria", "")) or _RE_ETAPA_EVENTO.search(f.get("evento", "")):
        return "Oficial"
    return "Treino"

ROOT = Path(__file__).parent
FONTE = ROOT / "data" / "folhas.json"
SAIDA = ROOT / "data.json"

# ALIASES — o mesmo piloto aparece com nome diferente entre folhas (Pietro, 17/07:
# "sim, sempre junta, usa o bom senso e junta").
# CRITERIO (o "bom senso" explicitado, pra nao virar chute): so junta quando o nome
# curto tem UM UNICO candidato completo no banco. Se dois nomes COMPLETOS dividem um
# token, sao pessoas DIFERENTES e ficam separados:
#   Antonio Lazaro != Antonio Carvalho · Fernando Adorno != Fernando Vilefort
#   Agostinho Neto != Agostinho Tozzo  · Gabriel Alves   != Gabriel Candelore
#   Carlos Magno != Carlos Silva != Carlos Alexandre     · Geraldo Neto != Agostinho Neto
# Nome novo ambiguo -> NAO adivinhar, perguntar ao Pietro.
ALIASES = {
    "Candelore": "Gabriel Candelore",   # unico *Candelore
    "Lira": "Rafael Lira",              # unico *Lira
    "Ltm": "Luciano Ltm",               # unico *Ltm
    "Rogerio": "Rogerio Belivacqua",    # 08/07 "Rogerio" (bare) = Belivacqua (Pietro confirmou 18/07)
    "Rogerio B.": "Rogerio Belivacqua", # "Rogerio B." (18/07 Bat02) = Belivacqua. "Rogerio T." e OUTRO piloto (Pietro nao sabe quem) -> SEPARADO.
    "Nickholas": "Nickholas R.",        # unico Nickholas*
    "Gustavo": "Gustavo Gondim",        # unico Gustavo*
    "Joao Vitor": "Joao Vitor Moura",   # unico Joao Vitor*
    "Willian Jr.": "William Jr.",       # erro de digitacao da folha de 27/06
    # das folhas de 25/06 (so primeiro nome):
    "Eduardo": "Eduardo Paiva",         # unico Eduardo*
    "Joao Carlos": "Joao Carlos Carvalho",  # unico Joao Carlos*
    "Geraldo": "Geraldo Neto",          # unico Geraldo*
    "Jonathan": "Jonathan Ribeiro",     # unico Jonathan*
    "Antonio L.": "Antonio Lazaro",     # o "L." desambigua contra Antonio Carvalho
    # das folhas de 08/08 (Campeonato Competikar Rental Kart, 1a Etapa 2o semestre):
    "Pietro A.": "Pietro",              # folha oficial usa nome+inicial do sobrenome
    "Caio Alexsander": "Caio Alexander",   # grafia varia entre as 3 folhas do dia; "Alexander" ja era o piloto existente
    "Carlos Alexsander": "Carlos Alexandre",  # idem — "Alexandre" ja era o piloto existente
    "Fernando Villefort": "Fernando Vilefort",  # 1 folha grafa com "ll", as outras 2 com "l" (+ historico)
    "Roniel": "Roniel Moreira",         # unico Roniel* — nome completo veio na folha de 08/08
    # Pietro confirmou por voz em 10/08/2026, perguntado nome a nome:
    # "esse Nicholas ai e o mesmo Nicholas, todos sao o mesmo. E o Joao, sim, pode contar
    #  tambem como um piloto so."
    # O teste de co-ocorrencia nao resolvia (nenhum dos pares dividiu bateria alguma vez),
    # entao a fusao veio DELE, nao de inferencia minha.
    "Nikolas": "Nickholas R.",          # 08/08 grafa "Nikolas"; ja havia Nickholas -> Nickholas R.
    "Joao Carvalho": "Joao Carlos Carvalho",  # 08/08 grafa curto; ja havia Joao Carlos -> Joao Carlos Carvalho
}

# AMBIGUOS — NAO juntar sem o Pietro dizer. Dois candidatos completos cada:
#   "Antonio"  (25/06 Bat.01) -> Antonio Lazaro OU Antonio Carvalho?
#   "Fernando" (25/06 Bat.02) -> Fernando Adorno OU Fernando Vilefort?
# Ficam como piloto proprio ate ele resolver. Chutar aqui corrompe o recorde de um
# deles em silencio - exatamente o erro de rotulo que ele ja mandou nao repetir.
AMBIGUOS = {"Antonio", "Fernando"}


def canon(nome: str) -> str:
    n = nome.strip()
    return ALIASES.get(n, n)


def to_seg(t: str) -> float:
    """'54.147' -> 54.147 | '1:19.130' -> 79.13 | '01:01.516' -> 61.516"""
    t = t.strip()
    if ":" in t:
        partes = t.split(":")
        return int(partes[-2]) * 60 + float(partes[-1])
    return float(t)


def fmt(seg: float) -> str:
    return f"{seg:.3f}" if seg < 60 else f"{int(seg // 60)}:{seg % 60:06.3f}"


def agregar(folhas: list) -> dict:
    """Roda a agregacao (melhor volta por piloto/tracado -> leaderboard/recordes/pilotos)
    sobre um subconjunto de folhas. Usado duas vezes em main(): uma com TODAS as folhas
    (geral) e outra so com as Oficiais — mesma logica, escopo diferente."""
    melhor: dict = {}
    total_resultados = 0
    for f in folhas:
        for r in f["resultados"]:
            nome, tracado = canon(r["nome"]), f["tracado"]
            seg = to_seg(r["melhor_volta"])
            total_resultados += 1
            k = (nome, tracado)
            if k not in melhor or seg < melhor[k]["seg"]:
                melhor[k] = {"piloto": nome, "tracado": tracado, "tempo": fmt(seg), "seg": seg,
                             "kart": r["kart"], "data": f["data"], "evento": f["evento"],
                             "categoria": f["categoria"]}

    tracados = sorted({f["tracado"] for f in folhas})

    leaderboard = {}
    for t in tracados:
        lst = sorted([v for v in melhor.values() if v["tracado"] == t], key=lambda x: x["seg"])
        for i, x in enumerate(lst, 1):
            x["rank"] = i
        leaderboard[t] = lst

    recordes = [dict(tracado=t, tempo=leaderboard[t][0]["tempo"], seg=leaderboard[t][0]["seg"],
                     piloto=leaderboard[t][0]["piloto"], kart=leaderboard[t][0]["kart"],
                     data=leaderboard[t][0]["data"], evento=leaderboard[t][0]["evento"],
                     categoria=leaderboard[t][0]["categoria"])
                for t in tracados if leaderboard[t]]

    pilotos = {}
    for v in melhor.values():
        p = pilotos.setdefault(v["piloto"], {"nome": v["piloto"], "kart": v["kart"], "por_tracado": {}, "aparicoes": 0})
        p["por_tracado"][v["tracado"]] = {"tempo": v["tempo"], "seg": v["seg"], "data": v["data"],
                                          "kart": v["kart"], "evento": v["evento"], "categoria": v["categoria"]}
    for p in pilotos.values():
        p["aparicoes"] = sum(1 for f in folhas for r in f["resultados"] if canon(r["nome"]) == p["nome"])
        bt = min(p["por_tracado"].items(), key=lambda kv: kv[1]["seg"])
        p["melhor_geral"], p["melhor_geral_seg"] = bt[1]["tempo"], bt[1]["seg"]
        p["melhor_geral_tracado"], p["kart"] = bt[0], bt[1]["kart"]
    lst = sorted(pilotos.values(), key=lambda x: x["melhor_geral_seg"])
    for i, p in enumerate(lst, 1):
        p["rank_geral"] = i

    return {"tracados": tracados, "leaderboard": leaderboard, "recordes": recordes,
            "pilotos": lst, "total_resultados": total_resultados}


def main() -> int:
    folhas = json.loads(FONTE.read_text(encoding="utf-8"))
    for f in folhas:
        f["categoria"] = categoria(f)

    folhas_oficiais = [f for f in folhas if f["categoria"] == "Oficial"]

    geral = agregar(folhas)
    oficial = agregar(folhas_oficiais)

    out = {
        "gerado_em": date.today().isoformat(),
        "fonte": "Folhas oficiais Competikar/LapTime confirmadas pelo Pietro",
        "meta": {"total_sessoes": len(folhas), "total_sessoes_oficiais": len(folhas_oficiais),
                 "total_sessoes_treino": len(folhas) - len(folhas_oficiais),
                 "total_pilotos": len(geral["pilotos"]), "total_pilotos_oficial": len(oficial["pilotos"]),
                 "total_resultados": geral["total_resultados"], "tracados": geral["tracados"],
                 "tracados_oficiais": oficial["tracados"]},
        "recordes_por_tracado": geral["recordes"],
        "leaderboard_por_tracado": geral["leaderboard"],
        "pilotos": geral["pilotos"],
        "oficial": {
            "recordes_por_tracado": oficial["recordes"],
            "leaderboard_por_tracado": oficial["leaderboard"],
            "pilotos": oficial["pilotos"],
        },
        "sessoes": folhas,
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(folhas)} folhas ({len(folhas_oficiais)} oficiais / {len(folhas)-len(folhas_oficiais)} treino) "
          f"| {len(geral['pilotos'])} pilotos | {geral['total_resultados']} resultados")
    for r in geral["recordes"]:
        print(f"  RECORDE {r['tracado']}: {r['piloto']} {r['tempo']} (kart {r['kart']}, {r['data']})")
    print("  -- recordes OFICIAIS --")
    for r in oficial["recordes"]:
        print(f"  RECORDE OFICIAL {r['tracado']}: {r['piloto']} {r['tempo']} (kart {r['kart']}, {r['data']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
