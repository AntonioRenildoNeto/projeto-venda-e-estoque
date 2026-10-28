# Roteiro dos testes Alfa e Beta

Coordenação: **Arthur Silva**. Os dois testes são feitos por pessoas, não por código: este roteiro serve para conduzir e registrar.

## Preparação (vale para os dois)

1. Rodar `python run.py` e abrir http://127.0.0.1:5000.
2. Entrar como Admin (`admin@sistema.com` / `admin123`).
3. Cadastrar pelo menos um produto de cada tipo (Alimento, Eletrônico, Vestuário).

---

## Teste Alfa — a equipe (Antonio, Arthur e Laerte)

Feito pelos três integrantes, em ambiente controlado, usando o sistema como se fossem o cliente. Cada um executa os passos dos seus módulos (Antonio: 1 a 6, a remoção de usuário do 13, 14 e 15; Arthur: 7, 8 e a remoção de produto do 13; Laerte: 9 a 12) e anota o que estranhar. O Arthur reúne tudo em um único registro.

| # | O que fazer | Resultado esperado | OK? | Observações / erro encontrado |
|---|---|---|---|---|
| 1 | Entrar com senha errada | Mensagem "E-mail ou senha incorretos" | | |
| 2 | Entrar como Admin | Vai para o início e mostra o nome no topo | | |
| 3 | Cadastrar usuário comum com todos os campos | Aparece na lista | | |
| 4 | Cadastrar usuário com e-mail inválido / telefone curto / ID repetido | Mensagem de erro clara, nada cadastrado | | |
| 5 | Sair e entrar com o usuário comum | Menu **não** mostra "Usuários" | | |
| 6 | Como comum, digitar `/usuarios` na barra de endereço | "Acesso negado" | | |
| 7 | Como Admin, cadastrar produto dos 3 tipos | Aparece na lista e no estoque com 0 | | |
| 8 | Cadastrar produto com preço negativo, nome vazio | Mensagem de erro | | |
| 9 | Registrar compra de 10 unidades | Estoque passa a 10 | | |
| 10 | Registrar venda de 3 unidades | Estoque passa a 7; total correto | | |
| 11 | Tentar vender mais do que há em estoque | Bloqueia com mensagem; estoque não muda | | |
| 12 | Cancelar a venda | Estoque volta a 10 | | |
| 13 | Remover produto e remover usuário | Somem das listas | | |
| 14 | Tentar remover o próprio Admin | Mensagem de que não pode | | |
| 15 | Usar o botão Voltar do navegador depois de sair | Não mostra dados; pede login | | |

Registrar cada erro encontrado na tabela de defeitos (abaixo). Depois de corrigir, rodar `python executar_testes.py regressao`.

---

## Teste Beta — pessoas de fora da equipe

Cada integrante convida **1 pessoa de fora da equipe** (colega, familiar), totalizando 3 testadores, para usarem o sistema sem ajuda, com poucas instruções: "Cadastre um produto, registre uma compra e uma venda e veja o estoque". Observar sem interferir e anotar onde a pessoa hesitou.

Perguntas para cada testador (nota de 1 a 5, 5 = ótimo):

| Pergunta | Nota | Comentário |
|---|---|---|
| Foi fácil entender o que fazer em cada tela? | | |
| As mensagens de erro e de sucesso foram claras? | | |
| Conseguiu concluir uma compra e uma venda sem ajuda? | | |
| Algo travou, sumiu ou deu resultado estranho? | | |
| O que você mudaria? | — | |

Testador: ______________________  Data: ____/____/______  Navegador: ____________

---

## Tabela de defeitos

| Nº | Quem achou | Teste (alfa/beta) | O que aconteceu | Gravidade (alta/média/baixa) | Corrigido? |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
