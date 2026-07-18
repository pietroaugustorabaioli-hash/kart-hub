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


def main() -> int:
    folhas = json.loads(FONTE.read_text(encoding="utf-8"))

    # melhor volta por (piloto, tracado) — dedup por nome, kart do melhor tempo
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
                             "kart": r["kart"], "data": f["data"], "evento": f["evento"]}

    tracados = sorted({f["tracado"] for f in folhas})

    leaderboard = {}
    for t in tracados:
        lst = sorted([v for v in melhor.values() if v["tracado"] == t], key=lambda x: x["seg"])
        for i, x in enumerate(lst, 1):
            x["rank"] = i
        leaderboard[t] = lst

    recordes = [dict(tracado=t, tempo=leaderboard[t][0]["tempo"], seg=leaderboard[t][0]["seg"],
                     piloto=leaderboard[t][0]["piloto"], kart=leaderboard[t][0]["kart"],
                     data=leaderboard[t][0]["data"], evento=leaderboard[t][0]["evento"])
                for t in tracados if leaderboard[t]]

    pilotos = {}
    for v in melhor.values():
        p = pilotos.setdefault(v["piloto"], {"nome": v["piloto"], "kart": v["kart"], "por_tracado": {}, "aparicoes": 0})
        p["por_tracado"][v["tracado"]] = {"tempo": v["tempo"], "seg": v["seg"], "data": v["data"],
                                          "kart": v["kart"], "evento": v["evento"]}
    for p in pilotos.values():
        p["aparicoes"] = sum(1 for f in folhas for r in f["resultados"] if canon(r["nome"]) == p["nome"])
        bt = min(p["por_tracado"].items(), key=lambda kv: kv[1]["seg"])
        p["melhor_geral"], p["melhor_geral_seg"] = bt[1]["tempo"], bt[1]["seg"]
        p["melhor_geral_tracado"], p["kart"] = bt[0], bt[1]["kart"]
    lst = sorted(pilotos.values(), key=lambda x: x["melhor_geral_seg"])
    for i, p in enumerate(lst, 1):
        p["rank_geral"] = i

    out = {
        "gerado_em": date.today().isoformat(),
        "fonte": "Folhas oficiais Competikar/LapTime confirmadas pelo Pietro",
        "meta": {"total_sessoes": len(folhas), "total_pilotos": len(lst),
                 "total_resultados": total_resultados, "tracados": tracados},
        "recordes_por_tracado": recordes,
        "leaderboard_por_tracado": leaderboard,
        "pilotos": lst,
        "sessoes": folhas,
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(folhas)} folhas | {len(lst)} pilotos | {total_resultados} resultados")
    for r in recordes:
        print(f"  RECORDE {r['tracado']}: {r['piloto']} {r['tempo']} (kart {r['kart']}, {r['data']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
