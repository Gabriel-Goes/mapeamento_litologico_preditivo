# QGIS local no Dell + PostgreSQL/PostGIS via túnel SSH

Este é o fluxo operacional preferencial para acessar o banco do Preditor
Terra a partir de um QGIS rodando no laptop, sem expor a porta `5432`
publicamente.

Arquitetura alvo:

- QGIS no Dell
- túnel SSH para o GeoServer na porta `62222`
- PostgreSQL/PostGIS escutando localmente no GeoServer em `127.0.0.1:5432`

## 1. Estado esperado no GeoServer

O PostgreSQL deve permanecer ativo no servidor e responder localmente:

```bash
sudo systemctl status postgresql.service
pg_isready -h 127.0.0.1 -p 5432
```

Validação mínima no servidor:

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d geologia -c "SELECT version();"
psql -h 127.0.0.1 -p 5432 -U postgres -d geologia -c "SELECT postgis_full_version();"
```

Validação dos objetos mínimos usados pelo repositório:

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d geologia -c \
  "SELECT to_regclass('carto.folhas_cartograficas'),
          to_regclass('litologia.litologia_100k'),
          to_regclass('geof.v_gamma_1082_corr');"
```

Se o serviço estiver ativo, mas `pg_isready` ou `psql` falharem, o banco não
está operacional para o QGIS ainda.

## 2. Contrato de segurança

Neste fluxo o PostgreSQL não precisa ficar acessível diretamente pela rede.
O acesso do QGIS acontece por SSH, então o banco pode continuar restrito ao
loopback do próprio GeoServer.

Diretriz do MVP:

- `listen_addresses` restrito ao host local
- autenticação por senha (`scram-sha-256`) em `pg_hba.conf`
- sem `trust` para o usuário do QGIS

Exemplo de regra em `pg_hba.conf` para túnel SSH:

```conf
host    geologia    skilpadde_qgis    127.0.0.1/32    scram-sha-256
host    geologia    skilpadde_qgis    ::1/128         scram-sha-256
```

Depois de editar `pg_hba.conf`:

```bash
sudo systemctl reload postgresql.service
```

## 3. Roles e schemas

O usuário do QGIS deve ter leitura nos schemas oficiais e escrita apenas no
próprio schema.

Contrato de permissões:

- leitura: `carto`, `geof`, `litologia`
- escrita: somente `skilpadde`
- promoção para schema oficial: manual, por operador

Exemplo mínimo de criação:

```sql
CREATE ROLE skilpadde_qgis LOGIN PASSWORD 'trocar-esta-senha';

GRANT CONNECT ON DATABASE geologia TO skilpadde_qgis;

GRANT USAGE ON SCHEMA carto TO skilpadde_qgis;
GRANT USAGE ON SCHEMA geof TO skilpadde_qgis;
GRANT USAGE ON SCHEMA litologia TO skilpadde_qgis;

GRANT SELECT ON ALL TABLES IN SCHEMA carto TO skilpadde_qgis;
GRANT SELECT ON ALL TABLES IN SCHEMA geof TO skilpadde_qgis;
GRANT SELECT ON ALL TABLES IN SCHEMA litologia TO skilpadde_qgis;

ALTER DEFAULT PRIVILEGES IN SCHEMA carto GRANT SELECT ON TABLES TO skilpadde_qgis;
ALTER DEFAULT PRIVILEGES IN SCHEMA geof GRANT SELECT ON TABLES TO skilpadde_qgis;
ALTER DEFAULT PRIVILEGES IN SCHEMA litologia GRANT SELECT ON TABLES TO skilpadde_qgis;

CREATE SCHEMA IF NOT EXISTS skilpadde AUTHORIZATION skilpadde_qgis;
GRANT USAGE, CREATE ON SCHEMA skilpadde TO skilpadde_qgis;
```

Se o usuário precisar criar layers editáveis no QGIS, isso deve acontecer em
`skilpadde.*`, nunca em `carto.*`, `geof.*` ou `litologia.*`.

## 4. Túnel SSH no Dell

No Dell, suba o túnel SSH antes de abrir o QGIS:

```bash
ssh -p 62222 -N -L 55432:127.0.0.1:5432 usuario@HOST_DO_GEOSERVER
```

Esse comando cria o seguinte mapeamento local:

- `127.0.0.1:55432` no Dell
- encaminhado para `127.0.0.1:5432` no GeoServer

Enquanto o túnel estiver aberto, o QGIS pode se conectar ao banco usando a
porta local `55432`.

## 5. Configuração do QGIS

No QGIS do Dell, configure a conexão PostgreSQL assim:

- Host: `127.0.0.1`
- Port: `55432`
- Database: `geologia`
- Username: `skilpadde_qgis`
- Password: a senha configurada no servidor

Opcionalmente, use `pg_service.conf` no cliente:

```ini
[preditor_geologia_tunnel]
host=127.0.0.1
port=55432
dbname=geologia
user=skilpadde_qgis
```

Com o túnel ativo, o QGIS deve:

- carregar camadas oficiais de `carto`, `geof` e `litologia`
- permitir criação/edição de camadas em `skilpadde`

## 6. Validação do repositório no GeoServer

Depois de o banco estar operacional, valide os checks do repositório no
próprio GeoServer:

```bash
cd /home/ggrl/projetos/PreditorTerra-terraX
export PG_HOST=127.0.0.1
export PG_PORT=5432
export PG_DB=geologia
export PG_USER=postgres
python -m adaptive.cli doctor --check-tables
```

Se a conexão passar, o contrato básico do Preditor Terra com PostgreSQL/PostGIS
está funcional.

## 7. Troubleshooting

### PostgreSQL ativo no `systemctl`, mas sem resposta no `pg_isready`

- confirme que o cluster terminou de subir
- confira `postgresql.conf`, `pg_hba.conf` e logs do serviço
- teste `psql -h 127.0.0.1 -p 5432` no próprio GeoServer

### Avisos de `collation version`

Esses avisos devem ser tratados como manutenção do cluster. Para este fluxo,
eles só são bloqueantes se consultas, autenticação ou inicialização passarem a
falhar.

### QGIS conecta, mas não consegue editar

- verifique se a tabela está em `skilpadde`
- confirme ownership e privilégios do schema/tabela
- confirme que o usuário não está tentando salvar em schema oficial

### QGIS não conecta pelo túnel

- confirme que o SSH remoto responde na porta `62222`
- confirme que o túnel está aberto no Dell
- valide localmente no Dell com:

```bash
pg_isready -h 127.0.0.1 -p 55432
```

## 8. Fluxo legado

O uso de QGIS remoto por X11 continua documentado em
[qgis_remoto_windows.md](./qgis_remoto_windows.md), mas não é mais o caminho
preferencial para acesso ao banco.
