# QGIS remoto no GeoServer via X11 (legado)

Este guia descreve o fluxo legado de usar o QGIS do próprio GeoServer em
sessão remota X11, mantendo o processamento e os dados no servidor.

Para acesso operacional ao PostgreSQL/PostGIS a partir de um QGIS local no
laptop, use o guia preferencial:

- [qgis_postgis_ssh_tunnel.md](./qgis_postgis_ssh_tunnel.md)

## 1. Pre-requisitos no servidor (GeoServer)

No servidor, dentro do repositório:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
chmod +x scripts/run_qgis_preditor.sh \
  scripts/run_qgis_preditor_remote.sh \
  scripts/run_qgis_preditor_demo.sh \
  scripts/check_qgis_remote_env.sh \
  scripts/collect_demo_evidence.sh \
  scripts/run_qgis_debug_cycle.sh \
  scripts/triage_preditor_logs.py
```

Opcional:

```bash
cp scripts/preditor_qgis.remote.env.example scripts/preditor_qgis.remote.env
# editar conforme necessario
```

## 2. Fluxo recomendado para demo estável (com logs)

No servidor (após conectar com `ssh -Y` ou cliente X11):

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
./scripts/run_qgis_preditor_demo.sh
```

Esse launcher já faz:

- diagnóstico remoto (`check_qgis_remote_env.sh`);
- profile limpo (`PreditorTerraClean`) em `.qgis_profiles`;
- log principal em `logs/preditor_terra.log`;
- captura completa da sessão em `logs/sessions/qgis_run_YYYYmmdd_HHMMSS.log`.

Após executar os fluxos no QGIS (SOM + Territorial), consolide evidências:

```bash
./scripts/collect_demo_evidence.sh
```

Isso gera um resumo markdown em `logs/sessions/demo_evidence_*.md`.

## 2.1 Ciclo completo de debug/reteste (recomendado)

Para executar o ciclo de engenharia (precheck -> execução -> evidências -> triagem):

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
./scripts/run_qgis_debug_cycle.sh --profile PreditorTerraClean --strict-gate
```

Saídas do ciclo:

- `logs/sessions/qgis_run_*.log` (sessão completa);
- `logs/sessions/demo_evidence_*.md` (resumo de evidências);
- `logs/sessions/debug_triage_*.json` e `.md` (triagem de severidade).

Se quiser apenas coletar/triagem sem abrir nova sessão do QGIS:

```bash
./scripts/run_qgis_debug_cycle.sh --collect-only
```

## 2.2 Validar sem esperar a execução longa terminar

Durante uma interpolação grande (ex.: folha 100k), valide rapidamente o que já foi concluído:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
tail -n 120 logs/preditor_terra.log
```

Sinais de progresso:
- `GAMA DB atualizado ...` e `Upload_geof ... concluído`.
- linhas por feature no interpolador (`feature=... | algo=linear`).

Para confirmar conclusão da interpolação sem abrir o QGIS:

```bash
rg -n "Interpolate ids=.*concluído|Fluxo rápido completo concluído|Prioridade territorial concluída" logs/preditor_terra.log | tail -n 10
```

Se quiser consolidar evidência parcial da sessão em andamento:

```bash
./scripts/run_qgis_debug_cycle.sh --collect-only --tag parcial_em_execucao
```

## 2.3 Gerar pacote de entrega para o Gamba (1 comando)

Depois de ter ao menos uma sessão válida (`qgis_run_*.log`), gere o dossiê + mensagem de envio:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
./scripts/prepare_gamba_mvp_delivery.sh --tag gamba_mvp_delivery
```

Saídas esperadas:
- `docs/gamba/entrega_mvp_YYYY-MM-DD.md`
- `docs/gamba/mensagem_gamba_YYYY-MM-DD.md`
- `logs/sessions/debug_triage_gamba_mvp_delivery_*.json`
- `logs/sessions/debug_triage_gamba_mvp_delivery_*.md`

Opcional: forçar a sessão-base usada no pacote:

```bash
./scripts/prepare_gamba_mvp_delivery.sh \
  --session-log logs/sessions/qgis_run_20260304_180619.log \
  --tag gamba_mvp_delivery
```

## 3. Opção legada no Windows: MobaXterm (com X11 embutido)

1. Abra o MobaXterm.
2. Crie sessão SSH para o GeoServer com `X11-Forwarding` habilitado.
3. Conecte e rode:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
./scripts/run_qgis_preditor_demo.sh
```

Se o diagnóstico passar, o QGIS remoto abre no Windows usando o ambiente do PreditorTerra.

## 4. Opção legada alternativa: OpenSSH + VcXsrv

1. Instale e inicie o VcXsrv no Windows.
2. No PowerShell, conecte com forwarding X11:

```powershell
ssh -Y usuario@IP_DO_GEOSERVER
```

3. No shell remoto:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
./scripts/run_qgis_preditor_demo.sh
```

## 5. Diagnóstico rápido

No servidor:

```bash
./scripts/check_qgis_remote_env.sh
```

Erros comuns:
- `DISPLAY vazio`: sessão sem X11 forwarding.
- `qgis não encontrado`: QGIS não instalado no PATH do servidor.
- travamento gráfico: manter `LIBGL_ALWAYS_SOFTWARE=1` no env remoto.

## 6. Observações

- Esse fluxo mantém dados e processamento no GeoServer; apenas a interface viaja para o Windows.
- Para uso diário do banco no QGIS, prefira o túnel SSH para PostgreSQL/PostGIS em vez de X11.
- Para uso diário no IPT, essa opção reduz variação de ambiente entre máquinas.
- Avisos de `collation version` no PostgreSQL podem aparecer no terminal e geralmente não bloqueiam a demo.
- Se aparecer `import_error: No module named 'pystac_client'`, o fluxo STAC ficará indisponível, mas SOM + territorial continuam funcionando.
- O launcher remoto agora exporta automaticamente as variáveis de `scripts/preditor_qgis.remote.env`; não é mais necessário rodar `set -a` manualmente antes dos scripts.
- Se aparecer `relação "ml.run" não existe`, inicialize o schema adaptativo:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
python -m adaptive.cli init-db --sql-file sql/adaptive_schema.sql
```
