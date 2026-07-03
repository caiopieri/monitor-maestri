# Maestri Interactive Monitor & Scheduler

Este projeto é um monitor interativo e agendador de tarefas para terminais rodando dentro do **Maestri** (um ambiente de workspace espacial para agentes de IA).

O script funciona sem dependências externas (usa apenas a biblioteca padrão do Python 3) e se comunica diretamente com a CLI local do `maestri`.

---

## Recursos principais

1. **Monitoramento automático de limite (Rate Limit):**
   * Identifica automaticamente quando agentes conectados no Maestri (como o `Claude Code` ou `Jarvis Codex`) atingem o limite de uso diário ou de sessão.
   * Lê a tela do terminal bloqueado para extrair o horário de desbloqueio (suporta formatos como `resets 9pm` ou `try again at 11:27 PM`).
   * Agenda e envia automaticamente a mensagem `"pode continuar"` no segundo exato em que o limite expirar.
   
2. **Menu interativo (Interface de linha de comando):**
   * Interface interativa rodando em tempo real enquanto os loops de agendamento ocorrem em segundo plano.
   
3. **Agendamento de tarefas personalizadas:**
   * Crie sequências de comandos personalizadas a serem executadas em um ou mais terminais.
   * **Execuções em sequência com delay:** Envie múltiplos passos ordenados (ex: passo 1: `/clear`, passo 2: `/model opus`, passo 3: `sua mensagem`) com intervalos de 3 segundos entre os envios.
   * **Horários flexíveis:** Agende usando horários relativos (ex: `5m`, `1h`, `30s`), horários específicos hoje/amanhã (ex: `23:30`), ou datas completas (`YYYY-MM-DD HH:MM`).

4. **Persistência de dados e tarefas recorrentes:**
   * Todos os agendamentos personalizados são guardados localmente em `tasks.json`.
   * **Tarefas diárias:** Suporte a tarefas recorrentes diárias que se re-agendam automaticamente após cada execução.
   * **Segurança de inicialização:** Tarefas únicas cujos horários expiraram com o monitor fechado são descartadas de forma segura ao reiniciar o script.

---

## Instalação

O script não exige instalação de pacotes externos (`pip`). É necessário apenas ter o **Python 3** instalado.

1. Clone o repositório ou copie os arquivos para a sua máquina:
   ```bash
   git clone https://github.com/caiopieri/monitor-maestri.git
   cd monitor-maestri
   ```

2. Certifique-se de que o executável `maestri` esteja configurado no seu `PATH` (o Maestri faz isso automaticamente nos terminais abertos dentro do canvas).

---

## Como usar

1. Abra um terminal dentro do Maestri e execute o script:
   ```bash
   python3 monitor.py
   ```

2. Você verá o prompt `maestri-monitor>`. A partir dele, você pode digitar os comandos:

### Comandos do Menu Interativo:

* `status` - Mostra o estado do monitoramento automático e lista detalhadamente todos os agendamentos ativos (tanto os de rate-limit quanto os personalizados).
* `toggle` - Ativa ou desativa o monitoramento automático de limite (inicia como **ATIVADO** por padrão).
* `schedule` - Inicia o assistente de agendamento personalizado:
  1. Lista os terminais conectados e pede para você digitar os números dos terminais alvo (separados por vírgula para disparar em múltiplos).
  2. Pede que digite passo a passo a sequência de mensagens. Pressione Enter sem texto para finalizar.
  3. Pergunta se a tarefa é recorrente (diária).
  4. Pede o horário de execução (seja relativo como `10m`, específico como `14:00` ou completo).
* `cancel` - Cancela um agendamento personalizado ativo fornecendo o ID correspondente.
* `help` - Mostra a ajuda rápida.
* `exit` - Encerra o script e encerra os serviços em segundo plano de forma limpa.

---

## Estrutura do Projeto

* `monitor.py` - Script principal contendo a interface e os threads de controle.
* `tasks.json` - Arquivo gerado automaticamente onde ficam salvos os agendamentos ativos.
* `monitor.log` - Registro de log detalhado das execuções em segundo plano.
