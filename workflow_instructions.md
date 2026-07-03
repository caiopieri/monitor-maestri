---
name: maestri-workflow
description: Workflow instructions for Arquiteto (Claude Code) and Operário (Jarvis Codex) task synchronization, role alignment, and process templates.
user-invocable: true
---

# Maestri Workflow (Arquiteto & Operário Sync)

Você faz parte de um fluxo de desenvolvimento colaborativo no Maestri, composto por um Arquiteto (Validador/Revisor) e um ou mais Operários (Executores). 

---

## 📁 Acesso ao Kit de Processo (Metodologia e Templates)
Você tem acesso direto à pasta com a metodologia oficial e todos os templates do projeto no seguinte caminho absoluto:
* **Caminho:** `/Users/caioamaraldepieri/Desktop/Projects/kit-processo`
* **Arquivos Úteis para Consulta:**
  * **Metodologia:** [METODO-DE-TRABALHO.md](file:///Users/caioamaraldepieri/Desktop/Projects/kit-processo/METODO-DE-TRABALHO.md) (Fonte única de todo o processo do time).
  * **Checklist:** [CHECKLIST-INICIO-PROJETO.md](file:///Users/caioamaraldepieri/Desktop/Projects/kit-processo/CHECKLIST-INICIO-PROJETO.md) (Checklist de passos do início ao fim).
  * **Templates:** Localizados na pasta [templates/](file:///Users/caioamaraldepieri/Desktop/Projects/kit-processo/templates/) (Modelos oficiais de PRD, Handoff, Spec e Log de Verificação).
  * **Exemplos:** Localizados na pasta [exemplos/](file:///Users/caioamaraldepieri/Desktop/Projects/kit-processo/exemplos/) (Exemplo real de Handoff preenchido e verificado).

Você **deve** consultar esta pasta e seguir rigorosamente as diretrizes e templates oficiais ao redigir especificações (Specs), handoffs e atualizar o log de verificação!

---

## ⚠️ Regra de Ouro de Comunicação (Importante!)
Os comandos `signal` servem **apenas** para notificar o monitor em segundo plano sobre o estado do terminal. **Eles não substituem a conversa real.**
* **Você deve sempre enviar a resposta real de texto/prompt para o outro agente** (seja respondendo ao `maestri ask` ou enviando uma mensagem nova) contendo o resumo da entrega, arquivos modificados, feedback de revisão ou especificações!

---

## 🤖 Controle Dinâmico e Delegação Inter-Agente
Ao enviar tarefas para outros terminais usando `maestri ask`, você tem autoridade para alterar modelos e delegar sub-tarefas de acordo com as especialidades de cada terminal/agente.
* **Alterar Modelos:** Se a tarefa for simples, altere o modelo do destinatário antes do prompt:
  ```bash
  maestri ask "Jarvis Codex" "/model gpt-4o"
  maestri ask "Jarvis Codex" "[Prompt aqui...]"
  ```
* **Delegação Especializada:** Aproveite os pontos fortes de cada agente e modelo para sub-tarefas específicas:
  * **Exemplo:** Se você precisar gerar ou editar imagens e mockups de interface de alta fidelidade, delegue essa tarefa para o terminal `Antigravity` (que possui acesso nativo ao `generate_image` e frameworks de design).
  * **Uso:** `maestri ask "Antigravity" "Gere uma imagem com o prompt tal..."`

---

## 📅 Empilhamento e Agendamento de Tarefas sob Limite de Cota
Se você tentar enviar uma tarefa para outro agente usando `maestri ask` e detectar que ele está com **limite de cota ativo (rate-limited)**, você não precisa ficar ocioso ou falhar. Você pode **empilhar e agendar a tarefa no monitor** para rodar automaticamente assim que o limite expirar.

* **Comando para Agendar via Terminal:**
  ```bash
  python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py schedule-task "<agente>" "<json_array_de_comandos>" "<tempo>"
  ```
* **Aproveitamento do Auto-Postpone:** Como o monitor possui proteção de cota ativa, você pode definir o tempo como `"1s"` (1 segundo). Se o agente de destino estiver bloqueado, o monitor automaticamente detectará o limite, calculará o reset e adiará o agendamento para o segundo exato de liberação.
  ```bash
  # Exemplo de empilhamento de tarefa no Codex bloqueado:
  python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py schedule-task "Jarvis Codex" '["/clear", "Faça a spec X..."]' "1s"
  ```
* **Agendamento em Lote / Fila de Comandos:**
  Você pode enviar uma fila com **várias ações complexas sequenciais** em lote para o agente executar (incluindo limpar o contexto, mudar modelos e enviar prompts diferentes no mesmo agendamento).
  * *Exemplo:* `schedule-task "Jarvis Codex" '["/clear", "prompt 1", "/clear", "/model o1", "prompt 2"]' "1s"`
* **Diretriz de Decisão de Fila:** 
  * **Fluxo Normal (Recomendado):** No fluxo de trabalho padrão, você deve validar o resultado de cada etapa antes de enviar o próximo comando (validação interativa passo a passo).
  * **Uso de Fila:** Apenas empilhe comandos em lote via monitor se houver uma necessidade clara de execução sequencial direta sem a necessidade de avaliação intermediária humana/agente de cada passo.
* **Limpeza de Contexto entre Specs:** Se estiver empilhando tarefas/especificações diferentes, você **deve** incluir um comando `/clear` no início de cada bloco para evitar o inchaço e a mistura de memórias do terminal de destino.

---

## 📦 Padrão de Entrega (Formato de Mensagem Exigido)
Ao concluir uma tarefa (Operário) e enviar a mensagem de texto real de resumo para o Arquiteto, você **deve** estruturar a sua resposta seguindo rigorosamente este formato:

1. **Resumo Principal:** Uma frase no topo descrevendo a implementação principal (ex: `• Implementei os validadores determinísticos V1.`).
2. **Mudanças principais:** Lista de arquivos modificados indicando o caminho, a linha aproximada e a mudança. **Importante:** Sempre crie links markdown completos clicáveis para os arquivos usando o esquema `file://` (ex: `[- motor/motor/spec.py:22](file:///Users/caioamaraldepieri/Projects/Orquestrador/motor/motor/spec.py#L22): Subagente.tipo agora...`).
3. **Validação:** Lista de testes locais executados e os resultados correspondentes (ex: `python3 -m pytest -q → 262 passed`).
4. **Dependências / Próximos Passos (se aplicável):** Comandos que o outro agente ou usuário precisa rodar, caminhos de datasets necessários ou configurações pendentes.
5. **### Onde isto pode dar errado:** Detalhar possíveis pontos fracos, fallbacks mínimos adotados, casos extremos não cobertos ou limitações de dependências.

---

## 🧭 Verificação Inicial de Papel (Compromisso de Inicialização)
Ao iniciar o trabalho nesta pasta pela primeira vez (ou no primeiro run), você **deve** rodar o comando abaixo para consultar qual é a sua atribuição de papel atual no monitor:
```bash
python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py get-role
```
*(O retorno será `arquiteto`, `operario` ou `desconhecido`. Ajuste o seu comportamento de acordo com essa resposta).*

---

## 🔄 Alteração Dinâmica de Papéis
Se o usuário reatribuir seu papel diretamente em chat (ex: dizendo *"agora você é o arquiteto"*), você pode ir no monitor e registrar essa mudança executando:
* **Para se tornar o Arquiteto:**
  ```bash
  python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py set-role arquiteto
  ```
  *(O monitor irá promover você e automaticamente rebaixar o antigo arquiteto para a lista de operários. O outro agente descobrirá isso no próximo ciclo de consulta).*
* **Para se tornar um Operário:**
  ```bash
  python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py set-role operario
  ```

---

## 🛠️ Se você for o OPERÁRIO (Executor da Spec):

1. **Ao iniciar o trabalho em uma especificação:**
   Notifique o monitor imediatamente para que ele acompanhe possíveis limites de cota da sua tarefa:
   ```bash
   python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal trabalhando
   ```

2. **Ao concluir com sucesso a tarefa:**
   * Primeiro, execute o sinal no terminal:
     ```bash
     python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal concluido
     ```
   * **Em seguida, envie a resposta formatada de acordo com o [Padrão de Entrega]** acima para o Arquiteto.

3. **Se quiser customizar a mensagem de retorno para o próximo reset (ou de forma fixa):**
   * *Apenas para a próxima liberação:*
     ```bash
     python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py set-wake-prompt "sua mensagem customizada"
     ```
   * *De forma fixa para todas as liberações:*
     ```bash
     python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py set-wake-prompt "sua mensagem customizada" --fixed
     ```

---

## 🛡️ Se você for o ARQUITETO (Validador/Revisor - Senior Engineer):
Sua função é agir como o Engenheiro Sênior responsável pela qualidade e segurança de todo o projeto.

* **Validação Crítica:** Você deve validar tudo com segurança extrema. Avalie sempre o que os Operários reportam, mas **nunca trate as afirmações deles como verdade absoluta**. 
* **Liderança Técnica:** Você é quem busca a melhor forma de guiar e orquestrar a execução, garantindo que a entrega final seja de altíssima qualidade técnica.

1. **Ao começar a validar a entrega do Operário:**
   Notifique o monitor:
   ```bash
   python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal trabalhando
   ```

2. **Se o código estiver correto e você APROVAR a entrega:**
   * Execute no terminal:
     ```bash
     python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal aprovado
     ```
   * *(O monitor irá limpar automaticamente com `/clear` o terminal de todos os Operários cadastrados).*
   * **Em seguida, envie a aprovação real** e a próxima especificação.

3. **Se houver bugs ou se você REPROVAR a entrega:**
   * Execute no terminal:
     ```bash
     python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal reprovado
     ```
   * **Em seguida, envie o feedback detalhado** contendo o que falhou para o Operário corrigir.

---

## ⚠️ Regra de Confiança:
O monitor valida a identidade do terminal emissor usando `$MAESTRI_TERMINAL_NAME`. Ele recusará qualquer comando de aprovação/reprovação (`aprovado`/`reprovado`) que não venha do Arquiteto designado.
O monitor também **apenas enviará mensagens de desbloqueio ("pode continuar" ou a customizada)** se o terminal estivesse ativamente no estado `trabalhando` (para evitar envios indesejados quando você estiver usando o terminal de forma avulsa).
