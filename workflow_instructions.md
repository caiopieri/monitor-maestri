# Instrução do Workflow de Desenvolvimento (Maestri Sync)

Você faz parte de um fluxo estruturado de desenvolvimento (Arquiteto e Operários) no Maestri. 

Independentemente de você ser o **Claude Code** ou o **Jarvis Codex**, siga as diretrizes abaixo dependendo do papel que o usuário designou a você na sessão atual. 

*(O monitor de terminal em segundo plano cuidará de validar sua identidade e autenticar os sinais por meio de regras de confiança)*:

---

## 🛠️ Se você for o OPERÁRIO (Executor da Spec):
Sempre que você concluir com sucesso a codificação e testes de uma tarefa/especificação solicitada, execute imediatamente no seu terminal o seguinte sinalizador:

```bash
python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal concluido
```

*(Isso avisará ao monitor que seu trabalho está pronto para revisão, mantendo o seu contexto de terminal ativo caso o Arquiteto encontre algum bug e reprove a entrega).*

---

## 🛡️ Se você for o ARQUITETO (Validador/Revisor):
Após analisar a implementação feita pelo(s) Operário(s):

### A. Se o código estiver correto e você APROVAR a entrega:
Execute em seu terminal:
```bash
python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal aprovado
```
*(O monitor irá limpar automaticamente o terminal do(s) Operário(s) para deixá-lo limpo para a próxima especificação).*

### B. Se houver bugs ou se você REPROVAR a entrega:
Execute em seu terminal:
```bash
python3 /Users/caioamaraldepieri/maestri-monitor/monitor.py signal reprovado
```
*(O monitor registrará o status de correção e o(s) Operário(s) deverão re-trabalhar mantendo a memória e contexto anteriores).*
