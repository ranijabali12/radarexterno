# 📡 Radar de Demanda Externa

Painel em HTML (projeto pessoal de estudo) que mostra onde e quando fatores externos — época do ano, clima, gripe/SRAG, dengue e buscas no Google — devem ajudar ou atrapalhar a procura de marcas e SKUs de Consumer Health. Recomendações por **região**.

## Como publicar no GitHub Pages (uma vez)
1. Crie um repositório no GitHub (ex.: `radar-demanda`).
2. Envie **todo o conteúdo desta pasta** (incluindo a pasta oculta `.github`). Pelo site: *Add file › Upload files* e arraste os arquivos e pastas.
3. **Settings › Pages** › *Source: Deploy from a branch* › Branch `main` / pasta `/ (root)` › Save. Em 1–2 minutos o link aparece no topo da página de Pages.
4. **Settings › Actions › General** › *Workflow permissions* › marque **Read and write permissions** › Save.
5. Aba **Actions** › *Atualizar dados do radar* › **Run workflow**. A primeira execução baixa o histórico de clima e leva ~15–20 min. Depois roda sozinha toda segunda-feira.

## Estrutura
- `index.html` — o painel (abre também direto no computador, com os dados embutidos).
- `data/sinais.json` — dados calculados pelo robô (atualizado automaticamente).
- `data/config.json` — marcas, pesos, perfis de SKU e relevância de mercado (fixa, pesquisa pública). Pode editar.
- `data/base/` — bases salvas usadas quando uma fonte falha (Fiocruz, Google Trends, histórico de clima).
- `scripts/atualizar.py` — o robô. Rodar local: `pip install -r scripts/requirements.txt` e `python scripts/atualizar.py` (ou `--offline` para usar só as bases).

## Fontes
InfoGripe/Fiocruz (SRAG) · Google Trends (via pytrends, instável — quando falha, o painel usa a base salva e mostra um aviso no topo) · Open-Meteo (clima histórico + previsão sazonal, uso não comercial) · InfoDengue (dengue).
