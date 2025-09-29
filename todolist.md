# Plano de Ação: Novas Funcionalidades do Dashboard

Este arquivo descreve o plano de ação para implementar as novas funcionalidades solicitadas. As tarefas foram executadas em sequência.

## Milestone 1: Backend - Modelo de Dados e Configuração

O objetivo deste marco é preparar o backend para armazenar e gerenciar as novas configurações do sistema (setpoints de temperatura, temporizadores, etc.).

- [x] **1.1: Modificar `sensor_server.py` para adicionar a nova página de controle.**
  - [x] Adicionar uma nova rota `/control` que renderiza um novo template `control.html`.

- [x] **1.2: Criar a tabela `settings` no banco de dados.**
  - [x] Em `dashboard.py`, modificar a função `init_database` para criar uma nova tabela `settings` com colunas (`setting_name TEXT PRIMARY KEY`, `setting_value REAL`).
  - [x] Adicionar valores padrão para as novas configurações na primeira inicialização.

- [x] **1.3: Criar API para gerenciar as configurações.**
  - [x] Em `sensor_server.py`, criar um endpoint `GET /api/settings` para ler todas as configurações.
  - [x] Em `sensor_server.py`, criar um endpoint `POST /api/settings` para atualizar uma ou mais configurações.

## Milestone 2: Frontend - Interface de Controle

Este marco foca na criação da nova interface web onde o usuário poderá visualizar e ajustar todos os novos parâmetros e controles.

- [x] **2.1: Criar o arquivo `templates/control.html`.**
  - [x] Desenvolver a estrutura da página com todos os 15 visores e botões solicitados.
  - [x] Usar Bootstrap para um layout responsivo e organizado.

- [x] **2.2: Criar o arquivo `static/js/control.js`.**
  - [x] Implementar a lógica para buscar os valores atuais das configurações da API (`GET /api/settings`) e preencher os campos da tela quando a página carregar.
  - [x] Adicionar `event listeners` para os botões e campos de ajuste. Quando um valor for alterado, enviar a atualização para o backend (`POST /api/settings`).

- [x] **2.3: Adicionar link de navegação para a nova página.**
  - [x] Em `templates/base.html`, adicionar um link na barra de navegação para a página `/control`.

## Milestone 3: Backend - Lógica de Controle Principal

Este é o marco mais complexo, onde a lógica de controle para o modo automático e manual foi implementada no script principal.

- [x] **3.1: Criar a tabela `commands` para comunicação.**
  - [x] Em `dashboard.py`, na função `init_database`, criar uma tabela `commands` (`id INTEGER PRIMARY KEY`, `command TEXT`, `payload TEXT`, `processed INTEGER DEFAULT 0`).
  - [x] Em `sensor_server.py`, criar endpoints de API (ex: `POST /api/command`) que recebem os comandos do frontend (ex: "ligar ventilador manual") e os inserem na tabela `commands`.

- [x] **3.2: Implementar a leitura de configurações e comandos em `dashboard.py`.**
  - [x] No loop principal de `dashboard.py`, adicionar uma função que periodicamente busca por novos comandos na tabela `commands`.
  - [x] Adicionar uma função que carrega as configurações da tabela `settings` no início e periodicamente.

- [x] **3.3: Implementar a máquina de estados (Manual/Automático).**
  - [x] Adicionar uma variável de estado para controlar o modo (`SYSTEM_MODE`).
  - [x] O estado será alterado por um comando vindo da interface.

- [x] **3.4: Implementar a lógica de controle do Forno (Modo Automático).**
  - [x] Com base na temperatura do forno e nos setpoints, acionar/desligar as saídas (GPIOs ou simulação) para o ventilador, resistência e rosca.
  - [x] Implementar os temporizadores para a resistência e para o ciclo da rosca de alimentação.

- [x] **3.5: Implementar a lógica para os acionamentos manuais.**
  - [x] Quando um comando de acionamento manual for recebido (ex: "ligar ventilador"), e o sistema estiver em modo `MANUAL`, acionar a saída correspondente.

- [x] **3.6: Garantir o funcionamento em modo de simulação.**
  - [x] Toda a lógica de controle deve funcionar sem a flag `--use-rpi`. Em vez de acionar GPIOs, o script deve imprimir o estado das saídas no console (ex: "SIMUL: Ventilador LIGADO").

## Milestone 4: Finalização e Testes

- [x] **4.1: Revisão completa do código.**
  - [x] Verificar se o código está limpo, comentado e se a interação entre frontend e backend está correta.
- [x] **4.2: Documentação.**
  - [x] Atualizar o `readme.md` para explicar as novas funcionalidades, a nova tela de controle e como usá-la.
- [x] **4.3: Teste final.**
  - [x] Fornecer os comandos para o usuário executar e testar o sistema completo.
