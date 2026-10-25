"""Extração (camada bronze) da Série Histórica de Preços de Combustíveis da ANP.

A ANP publica dois tipos de arquivo com o mesmo layout (preço coletado por posto):
  - semestrais "ca" (combustíveis automotivos): dsas/ca/ca-AAAA-SS.csv|zip
  - mensais de gasolina/etanol:                 dsan/AAAA/<nome irregular com o mês>.csv

Os nomes dos mensais variam muito (ex.: "02-cados-abertos-preco-gasolina-etanol.csv"),
por isso lemos os links da página em vez de montar URLs. Regra de seleção:
  semestral sempre que existir; mensal só para meses que nenhum semestral cobre.

Os arquivos vão para data/bronze/anp/ convertidos para UTF-8 (2021 vem em Latin-1,
os mais novos em UTF-8 com BOM). Fora o encoding, o conteúdo fica como foi publicado.
"""

import io
import json
import logging
import re
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

log = logging.getLogger(__name__)

PAGINA_ANP = ("https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
              "serie-historica-de-precos-de-combustiveis")
BRONZE = Path("/opt/airflow/data/bronze/anp")
ANO_INICIAL = 2021
HEADERS = {"User-Agent": "pipeline-combustiveis/1.0 (estudo; dados abertos ANP)"}

RE_SEMESTRAL = re.compile(r"/shpc/dsas/ca/ca-(\d{4})-(0[12])\.(csv|zip)$")
RE_MENSAL = re.compile(r"/shpc/dsan/(\d{4})/([^/]*gasolina-etanol[^/]*)\.csv$")


@dataclass
class Arquivo:
    url: str
    tipo: str      # "semestral" | "mensal"
    ano: int
    periodo: int   # semestre (1-2) ou mês (1-12)

    @property
    def nome_local(self) -> str:
        if self.tipo == "semestral":
            return f"semestral_{self.ano}-S{self.periodo}.csv"
        return f"mensal_{self.ano}-{self.periodo:02d}.csv"

    @property
    def meses(self) -> set[tuple[int, int]]:
        if self.tipo == "semestral":
            ini = 1 if self.periodo == 1 else 7
            return {(self.ano, m) for m in range(ini, ini + 6)}
        return {(self.ano, self.periodo)}


def listar_arquivos() -> list[Arquivo]:
    html = requests.get(PAGINA_ANP, headers=HEADERS, timeout=60).text
    links = set(re.findall(r'href="(https?://[^"]+\.(?:csv|zip))"', html))
    achados = []
    for url in links:
        if m := RE_SEMESTRAL.search(url):
            achados.append(Arquivo(url, "semestral", int(m[1]), int(m[2])))
        elif m := RE_MENSAL.search(url):
            # o mês é o primeiro número de 2 dígitos no nome que não faz parte do ano
            nome = re.sub(r"20\d{2}", "", m[2])
            mes = re.search(r"(?<!\d)(0[1-9]|1[0-2])(?!\d)", nome)
            if mes:
                achados.append(Arquivo(url, "mensal", int(m[1]), int(mes[1])))
            else:
                log.warning("Não consegui identificar o mês de %s — ignorado", url)
    return [a for a in achados if a.ano >= ANO_INICIAL]


def selecionar(arquivos: list[Arquivo]) -> list[Arquivo]:
    semestrais = [a for a in arquivos if a.tipo == "semestral"]
    cobertos = set().union(*(a.meses for a in semestrais)) if semestrais else set()
    mensais = {}
    for a in arquivos:
        if a.tipo == "mensal" and (a.ano, a.periodo) not in cobertos:
            mensais[(a.ano, a.periodo)] = a  # se houver duplicata, fica uma só
    return sorted(semestrais + list(mensais.values()), key=lambda a: (a.ano, min(a.meses)))


def _para_utf8(conteudo: bytes) -> bytes:
    if conteudo.startswith(b"\xef\xbb\xbf"):
        conteudo = conteudo[3:]
    try:
        conteudo.decode("utf-8")
        return conteudo
    except UnicodeDecodeError:
        return conteudo.decode("latin-1").encode("utf-8")


def _get(url: str, tentativas: int = 3) -> bytes:
    # o servidor do gov.br às vezes derruba a conexão no meio do download
    for i in range(1, tentativas + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=600)
            resp.raise_for_status()
            return resp.content
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
            if i == tentativas:
                raise
            log.warning("Falha ao baixar %s (tentativa %d): %s", url, i, e)
            time.sleep(15 * i)


def baixar(arq: Arquivo, destino: Path) -> None:
    log.info("Baixando %s", arq.url)
    conteudo = _get(arq.url)
    if arq.url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if len(csvs) != 1:
                raise ValueError(f"Esperava 1 CSV dentro de {arq.url}, achei {csvs}")
            conteudo = z.read(csvs[0])
    if not conteudo.split(b"\n", 1)[0].lstrip(b"\xef\xbb\xbf").startswith(b"Regiao - Sigla"):
        raise ValueError(f"Cabeçalho inesperado em {arq.url}")
    tmp = destino.with_suffix(".part")
    tmp.write_bytes(_para_utf8(conteudo))
    tmp.rename(destino)  # rename atômico: nunca fica arquivo pela metade com nome final


def extrair() -> dict:
    """Baixa o que falta e grava data/bronze/anp/manifest.json com os arquivos selecionados."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    selecionados = selecionar(listar_arquivos())
    if not selecionados:
        raise RuntimeError("Nenhum arquivo encontrado na página da ANP — o layout mudou?")

    baixados = 0
    for arq in selecionados:
        destino = BRONZE / arq.nome_local
        if destino.exists():
            continue
        baixar(arq, destino)
        baixados += 1

    # Mensais que passaram a ser cobertos por um semestral novo saem da bronze
    nomes = {a.nome_local for a in selecionados}
    removidos = []
    for f in BRONZE.glob("*.csv"):
        if f.name not in nomes:
            f.unlink()
            removidos.append(f.name)

    manifest = {"arquivos": [asdict(a) | {"arquivo": a.nome_local} for a in selecionados]}
    (BRONZE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    resumo = {"selecionados": len(selecionados), "baixados": baixados, "removidos": removidos}
    log.info("Extração concluída: %s", resumo)
    return resumo
